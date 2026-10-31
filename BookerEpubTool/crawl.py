# -*- coding: utf-8 -*-
import gc
import os
import re
import json
import logging
import traceback
from pyquery import PyQuery as pq
import readability
from os import path
from concurrent.futures import ThreadPoolExecutor
from typing import *
from .crawl_agent import CrawlAgent
from .crawl_models import *
from .util import to_kebab, md5
from .openai import logger as oai_logger
from .crawl_img import config as crawl_config
from .crawl_img import process_img as crawl_process_img, set_img_pool
from GenEpub import gen_epub

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s][%(name)s][%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class CrawlOrchestrator:

    def __init__(self, args):
        self.args = args
        self.agent = CrawlAgent(args)
        self.asset_dir = self.agent.asset_dir
        self.imgs = {}
        self.articles = []
        self.page_pool = ThreadPoolExecutor(args.page_threads)
        self.img_pool = ThreadPoolExecutor(args.img_threads)
        set_img_pool(self.img_pool)
        self._init_crawl_config()

    def _init_crawl_config(self):
        """同步 EpubCrawler 全局配置"""
        args = self.args
        crawl_config['headers'] = {'User-Agent': args.user_agent}
        if args.cookie:
            crawl_config['headers']['Cookie'] = args.cookie
        if args.referer:
            crawl_config['headers']['Referer'] = args.referer
        crawl_config['retry'] = args.http_retry
        crawl_config['timeout'] = (
            args.conn_timeout, args.read_timeout,
        )
        crawl_config['checkStatus'] = not args.no_check_status
        crawl_config['checkBlank'] = not args.no_check_blank
        crawl_config['wait'] = args.wait
        crawl_config['optiMode'] = args.opti_mode
        crawl_config['imgSrc'] = args.img_src.split(',')
        crawl_config['credit'] = not args.no_credit
        crawl_config['cache'] = not args.no_cache

    def run(self):
        args = self.args
        logger.info(args)
        self.step_fetch_index()
        self.step_extract_toc()
        self.step_crawl_chapters()
        self.step_gen_epub()
        gc.collect()
        logger.info('[*] 完成')

    # ── 步骤 ──────────────────────────────────

    def step_fetch_index(self):
        """[1] 抓取目录页"""
        args = self.args
        logger.info('[1] 抓取目录页')
        self.index_html = self.agent.fetch(args.url)
        self.name = self._extract_name(self.index_html)
        logger.info(f'书名: {self.name}')

    def _extract_name(self, html):
        args = self.args
        if args.name:
            return args.name
        m = re.search(r'<title[^>]*>(.*?)</title>', html, re.S | re.I)
        if m and m.group(1).strip():
            return m.group(1).strip()
        return to_kebab(args.url) or 'book'

    def step_extract_toc(self):
        """[2] 提取目录"""
        logger.info('[2] 提取目录')
        if self.args.url_list_file:
            urls = open(self.args.url_list_file, encoding='utf8').read().split('\n')
            urls = [u for u in urls if u.strip()]
            logger.info(f'章节数: {len(urls)}')
            self.toc = [
                TocItem(no=i+1, title='', href=url)
                for i, url in enumerate(urls)
            ]
            return

        anchors = self.agent.extract_anchors(
            self.index_html, self.args.url
        )
        logger.info(f'候选链接: {len(anchors)}')
        self.toc = self.agent.extract_toc(anchors)
        self.toc = self._norm_toc(self.toc)
        logger.info(f'章节数: {len(self.toc)}')

    def _norm_toc(self, toc):
        """按 no 排序、去重、补齐序号的目录列表"""
        seen = set()
        res = []
        for it in sorted(toc, key=lambda x: x.no):
            if it.no in seen:
                continue
            seen.add(it.no)
            res.append(it)
        return res

    def step_crawl_chapters(self):
        """[3] 并发抓取章节"""
        logger.info('[3] 并发抓取章节')
        hdls = {}
        for i, item in enumerate(self.toc):
            hdls[i] = self.page_pool.submit(
                self._crawl_article_safe, i, item,
            )
        articles = [None] * len(hdls)
        for i, h in hdls.items():
            articles[i] = h.result()
        self.articles = [a for a in articles if a]
        self.imgs = {
            k: v for k, v in self.imgs.items()
            if v
        }
        logger.info(
            f'成功: {len(self.articles)}/{len(hdls)}'
        )

    def _crawl_article_safe(self, i, item):
        try:
            return self._crawl_article(i, item)
        except KeyboardInterrupt:
            raise
        except Exception:
            logger.warn(
                f'{i} <{item.title}> 抓取失败: '
                + traceback.format_exc()
            )
            return None

    def _crawl_article(self, i, item):
        logger.info(f'[3] {item.href or item.title}')
        # 判断是否是纯标题章节
        if not item.href:
            return {'title': item.title, 'content': ''}
        # 读缓存
        hash = md5(item.href)
        art = self.load_article(hash)
        if art and not self.args.no_cache:
            return art
        html = self.agent.fetch(item.href)
        art = {}
        if self.args.llm:
            res = self.agent.extract_article(html, url=item.href)
            art['title'] = res.title or item.title
            art['content'] = res.content or ''
        else:
            rt = pq(html)
            el_title = rt.find(self.args.title).eq(0)
            art['title'] = (el_title.text() or '').strip()
            el_title.remove()
            art['content'] = (
                rt.find(self.args.content).html() or ''
                if self.args.content
                else readability.Document(html)
                    .summary(html_partial=True)
            )
        art['content'] = crawl_process_img(
            art['content'],
            self.imgs,
            page_url=item.href,
            img_prefix='../Images/',
        )
        self.save_article(hash, art)
        return art

    def step_gen_epub(self):
        """[4] 生成 EPUB"""
        logger.info('[4] 生成 EPUB')
        args = self.args
        if args.name:
            articles = [{
                'title': self.name,
                'content': (
                    f"<p>来源：<a href='{args.url}'>{args.url}</a></p>"
                ),
            }] + self.articles
        else:
            articles = self.articles
        gen_epub(
            articles, self.imgs,
            name=self.name,
            limit=args.size_limit,
        )
        logger.info(f'输出: {args.name}.epub')


    def load_article(self, hash):
        fname = path.join(self.asset_dir, f'{hash}.json')
        if not path.isfile(fname):
            return None
        try:
            art = json.loads(open(fname, encoding='utf8').read())
        except Exception as ex: 
            print(ex)
            return None
            
        if isinstance(art, dict) and \
            art.get('title', '') and \
            art.get('content', ''):
            return art
        else:
            return None
            
    def save_article(self, hash, art):
        os.makedirs(self.asset_dir, exist_ok=True)
        fname = path.join(self.asset_dir, f'{hash}.json')
        open(fname, 'w', encoding='utf-8').write(json.dumps(art))

def crawl(args):
    if args.debug:
        logger.setLevel(logging.DEBUG)
        oai_logger.setLevel(logging.DEBUG)
    try:
        CrawlOrchestrator(args).run()
    except KeyboardInterrupt:
        raise
    except Exception:
        logger.warn(traceback.format_exc())


def reg_subparser(subparsers):
    crawl_parser = subparsers.add_parser(
        "crawl", help="抓取网页生成 EPUB"
    )
    crawl_parser.add_argument("url", help="书籍目录页 URL")
    crawl_parser.add_argument(
        "-n", "--name", default='',
        help="书名（默认取网页 <title>）"
    )
    crawl_parser.add_argument(
        "-e", "--encoding", default='utf-8',
        help="网页编码"
    )
    crawl_parser.add_argument(
        "-pt", "--page-threads", type=int, default=8,
        help="章节抓取线程数"
    )
    crawl_parser.add_argument(
        "-it", "--img-threads", type=int, default=24,
        help="图片下载线程数"
    )
    crawl_parser.add_argument(
        "-hr", "--http-retry", type=int, default=10,
        help="HTTP 请求重试次数"
    )
    crawl_parser.add_argument(
        "-CS", "--no-check-status", action='store_true',
        help="不检查 HTTP 请求状态码"
    )
    crawl_parser.add_argument(
        "-CB", "--no-check-blank", action='store_true',
        help="不检查标题和正文是否为空"
    )
    crawl_parser.add_argument(
        "-w", "--wait", type=float, default=0,
        help="每次请求后的等待秒数"
    )
    crawl_parser.add_argument(
        "-om", "--opti-mode", default='quant',
        help="图像压缩方式"
    )
    crawl_parser.add_argument(
        "-is", "--img-src", default='data-src,data-original-src,src',
        help="图像 URL 属性名称，逗号分隔"
    )
    crawl_parser.add_argument(
        "-ck", "--cookie", default='',
        help="Cookie"
    )
    crawl_parser.add_argument(
        "-rf", "--referer", default='',
        help="Referer"
    )
    crawl_parser.add_argument(
        "-CR", "--no-credit", action='store_true',
        help="是否不添加原文链接"
    )
    crawl_parser.add_argument(
        "-CC", "--no-cache", action='store_true',
        help="是否不读取缓存"
    )
    crawl_parser.add_argument(
        "-ml", "--max-len", type=int, default=20000,
        help="传入大模型的正文 HTML 最大长度"
    )
    crawl_parser.add_argument(
        "-sl", "--size-limit", default='50m',
        help="EPUB 分卷大小上限"
    )
    crawl_parser.add_argument(
        "-ul", "--url-list-file", default='',
        help="URL 列表文件，用于手动指定目录"
    )
    crawl_parser.add_argument(
        "--llm", action='store_true',
        help="强制使用 LLM 提取正文和标题"
    )
    crawl_parser.add_argument(
        "-tl",  "--title", default='title',
        help="标题选择器（默认为 <title>）"
    )
    crawl_parser.add_argument(
        "-co",  "--content", default='',
        help="内容选择器（默认用 readbility 自动识别）"
    )
    crawl_parser.set_defaults(func=crawl)