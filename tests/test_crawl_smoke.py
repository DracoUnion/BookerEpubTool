# -*- coding: utf-8 -*-
"""crawl 子命令冒烟测试（不调用 API）。

覆盖：模块导入链、解析辅助函数、端到端流程（本地 HTTP 服务器 + 模拟 LLM）。
"""

import os
import re
import zipfile
import threading
from argparse import Namespace
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import List

import pytest
from functools import partial

from BookerEpubTool.crawl import CrawlOrchestrator, reg_subparser
from BookerEpubTool.crawl_agent import CrawlAgent
from BookerEpubTool.crawl_models import (
    AnchorLink, TocItem, ArticleResult,
)
from BookerEpubTool.crawl_pmt import (
    EXTRACT_TOC_PMT, EXTRACT_ARTICLE_PMT,
)


def make_args(**kw):
    base = dict(
        url='',
        out='',
        name='',
        encoding='utf-8',
        page_threads=4,
        img_threads=4,
        http_retry=2,
        check_status=False,
        check_blank=False,
        wait=0,
        max_len=20000,
        size_limit='50m',
        debug=False,
        model='test-model',
        key='k',
        host='http://127.0.0.1',
        temp=1,
        stream=False,
        extra_body=None,
        max_tokens=None,
        user_agent='test',
        conn_timeout=5,
        read_timeout=5,
    )
    base.update(kw)
    return Namespace(**base)


def test_import_chain():
    import BookerEpubTool.crawl
    import BookerEpubTool.crawl_agent
    import BookerEpubTool.crawl_models
    import BookerEpubTool.crawl_pmt
    assert BookerEpubTool.crawl.CrawlOrchestrator is not None


def test_parse_list_with_code_block():
    from BookerEpubTool.util import ext_code_block
    from pydantic import parse_obj_as
    import json_repair
    ans = '```\n[{"no": 1, "title": "第一章", "href": "http://x/1"}]\n```'
    data = json_repair.loads(ext_code_block(ans))
    res = parse_obj_as(List[TocItem], data)
    assert res[0].no == 1
    assert res[0].title == '第一章'


def test_extract_anchors():
    agent = CrawlAgent(make_args())
    html = '''
    <a href="/c1.html">第一章</a>
    <a href="/c2.html">第二章</a>
    <a href="#top">返回顶部</a>
    '''
    anchors = agent.extract_anchors(html, 'http://example.com/')
    hrefs = [a.href for a in anchors]
    assert 'http://example.com/c1.html' in hrefs
    assert 'http://example.com/c2.html' in hrefs
    assert '#top' not in hrefs


def test_clean_html():
    agent = CrawlAgent(make_args())
    html = '''
    <html><body>
    <script>bad()</script>
    <nav>menu</nav>
    <p>正文</p>
    </body></html>
    '''
    clean = agent.clean_html(html)
    assert 'bad()' not in clean
    assert 'menu' not in clean
    assert '正文' in clean


# ── 端到端 ──────────────────────────────

SITE_INDEX = '''
<!DOCTYPE html>
<html><head><title>测试书</title></head><body>
<a href="/c1.html">第一章</a>
<a href="/c2.html">第二章</a>
<a href="/about">关于</a>
</body></html>
'''

SITE_C1 = '''
<!DOCTYPE html>
<html><head><title>第一章 开始</title></head><body>
<nav>导航</nav>
<p>这是第一章内容。</p>
<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==">
</body></html>
'''

SITE_C2 = '''
<!DOCTYPE html>
<html><head><title>第二章 进阶</title></head><body>
<p>这是第二章内容。</p>
</body></html>
'''


class _SiteHandler(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@pytest.fixture(scope='module')
def site():
    import tempfile
    import pathlib
    tmp = pathlib.Path(tempfile.mkdtemp())
    (tmp / 'index.html').write_text(SITE_INDEX, encoding='utf-8')
    (tmp / 'c1.html').write_text(SITE_C1, encoding='utf-8')
    (tmp / 'c2.html').write_text(SITE_C2, encoding='utf-8')
    handler = partial(_SiteHandler, directory=str(tmp))
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown()


def run_crawl(url, out, monkeypatch, **kw):
    from pyquery import PyQuery as pq
    import re as _re

    agent = CrawlAgent(make_args(url=url, out=out, **kw))

    # 模拟 LLM：由 prompt 关键词返回固定结果
    def fake_extract_toc(anchors):
        return [
            TocItem(no=0, title='第一章', href=url + '/c1.html'),
            TocItem(no=1, title='第二章', href=url + '/c2.html'),
        ]

    def fake_extract_article(html, url=''):
        root = pq(html)
        title = (root('title').text() or '').strip()
        root('nav, script, style, header, footer, aside').remove()
        body = root('body')
        content = body.html() or ''
        if not content:
            content = str(root)
        return ArticleResult(title=title, content=content)

    monkeypatch.setattr(agent, 'extract_toc', fake_extract_toc)
    monkeypatch.setattr(agent, 'extract_article', fake_extract_article)

    orch = CrawlOrchestrator(make_args(url=url, out=out, **kw))
    # 复用同一个 agent（已打补丁）
    orch.agent = agent
    orch.run()
    return orch


def test_crawl_end_to_end(site, tmp_path, monkeypatch):
    out = str(tmp_path / '测试书.epub')
    orch = run_crawl(site, out, monkeypatch, name='')
    assert orch.name == '测试书'  # 从 <title> 提取
    assert len(orch.articles) == 2

    # EPUB 应包含所有章节
    assert os.path.isfile(out)
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        assert 'mimetype' in names

        # 正文文件应存在
        text_files = [n for n in names if n.startswith('OEBPS/Text/')]
        assert len(text_files) >= 2

        # 目录应包含章节标题
        all_text = '\n'.join(
            z.read(n).decode('utf-8', 'ignore')
            for n in text_files
        )
        assert '第一章 开始' in all_text
        assert '第二章 进阶' in all_text

        # 图片应被处理并打包
        img_files = [n for n in names if n.startswith('OEBPS/Images/')]
        assert len(img_files) >= 1


def test_reg_subparser():
    import argparse
    parser = argparse.ArgumentParser()
    subp = parser.add_subparsers()
    reg_subparser(subp)
    args = parser.parse_args(['crawl', 'http://example.com/', '-o', 'x.epub', '-n', '书'])
    assert args.out == 'x.epub'
    assert args.name == '书'
    assert callable(args.func)