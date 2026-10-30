# -*- coding: utf-8 -*-
import re
import os
import tempfile
import json_repair
from os import path
from urllib.parse import urljoin
from pyquery import PyQuery as pq
from pydantic import BaseModel, parse_obj_as
import json
from typing import *
from .util import request_retry
from .crawl_pmt import *
from .crawl_models import *
from .util import (
    gen_objs_md5,
    render_prompt,
    ext_code_block,
    read_yaml_model,
    write_yaml_model,
    md5,
)
from .openai import OpenAIClient
import EpubCrawler


class CrawlAgent:

    def __init__(self, args):
        self.args = args
        self.asset_dir = path.join(
            tempfile.gettempdir(), 'booker_crawl'
        )
        os.makedirs(self.asset_dir, exist_ok=True)
        self.llm = OpenAIClient.from_args(args)

    # ── 网页请求 ──────────────────────────────

    def fetch(self, url: str) -> str:
        """抓取网页，返回 HTML 文本"""
        args = self.args
        hdrs = {'User-Agent': args.user_agent}
        if args.cookie:
            hdrs['Cookie'] = args.cookie
        if args.referer:
            hdrs['Referer'] = args.referer
        r = request_retry(
            'GET', url,
            retry=args.http_retry,
            check_status=not args.no_check_status,
            headers=hdrs,
            timeout=(args.conn_timeout, args.read_timeout),
            verify=False,
        )
        return r.content.decode(args.encoding, 'ignore')

    # ── 提取目录 ──────────────────────────────

    def extract_anchors(self, html: str, base_url: str) -> List[AnchorLink]:
        """从目录页 HTML 中提取所有候选链接"""
        root = pq(html)
        anchors: List[AnchorLink] = []
        vis = set()
        for el in root('a').items():
            text = (el.text() or '').strip()
            href = (el.attr('href') or '').strip()
            if not text or not href:
                continue
            href = re.sub(r'#.*$', '', href)
            href = urljoin(base_url, href)
            if not re.search(r'^https?://', href):
                continue
            if href in vis:
                continue
            vis.add(href)
            anchors.append(AnchorLink(
                no=len(anchors),
                text=re.sub(r'\s+', ' ', text)[:80],
                href=href,
            ))
            if len(anchors) >= 500:
                break
        return anchors

    def extract_toc(self, anchors: List[AnchorLink]) -> List[TocItem]:
        """用大模型从候选链接中提取章节目录"""
        cache_fname = path.join(
            self.asset_dir,
            'toc_' + gen_objs_md5(anchors) + '.yaml'
        )
        res = read_yaml_model(cache_fname, List[TocItem])
        if res is not None:
            return res
        lines = '\n'.join([
            f'{a.no}\t{a.text}\t{a.href}'
            for a in anchors
        ])
        ques = render_prompt(EXTRACT_TOC_PMT, anchors=lines)
        parse_output = lambda s: self._parse_list(s, TocItem)
        res: List[TocItem] = self.llm.ask_chatgpt_retry(
            ques, self.args.model, self.args, parse_output,
        )
        write_yaml_model(cache_fname, res)
        return res

    # ── 提取正文 ──────────────────────────────

    def clean_html(self, html: str) -> str:
        """去除无关标签，保留正文结构"""
        html = re.sub(r'<\?xml[^>]*\?>', '', html)
        html = re.sub(r'xmlns(:?\w+)?=".+?"', '', html)
        root = pq(html)
        root('script, style, noscript, iframe, nav, header, footer, aside').remove()
        return str(root)

    def extract_article(self, html: str, url: str = '') -> ArticleResult:
        """用大模型从章节网页中提取标题和正文 HTML"""
        if url:
            cache_fname = path.join(
                self.asset_dir,
                'art_' + md5(url) + '.yaml'
            )
        else:
            cache_fname = path.join(
                self.asset_dir,
                'art_' + gen_objs_md5(html) + '.yaml'
            )
        res = read_yaml_model(cache_fname, ArticleResult)
        if res is not None:
            return res
        html = self.clean_html(html)
        if self.args.max_len and len(html) > self.args.max_len:
            html = html[:self.args.max_len]
        ques = render_prompt(EXTRACT_ARTICLE_PMT, html=html)
        parse_output = lambda s: self._parse_obj(s, ArticleResult)
        res: ArticleResult = self.llm.ask_chatgpt_retry(
            ques, self.args.model, self.args, parse_output,
        )
        if not self.args.no_check_blank and \
           (res.title == '' or res.content == ''):
            raise ValueError('标题或正文为空')
        if not self.args.no_credit:
            res.content = \
                f'<blockquote>原文：<a href="{url}">' + \
                f'{url}</a></blockquote>' + res.content
        write_yaml_model(cache_fname, res)
        return res

    # ── 解析辅助 ──────────────────────────────

    def _parse_list(self, ans: str, model: Type[BaseModel]):
        return parse_obj_as(
            List[model],
            json_repair.loads(ext_code_block(ans)),
        )

    def _parse_obj(self, ans: str, model: Type[BaseModel]):
        return parse_obj_as(
            model,
            json_repair.loads(ext_code_block(ans)),
        )