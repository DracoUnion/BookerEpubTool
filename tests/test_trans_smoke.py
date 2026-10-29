# -*- coding: utf-8 -*-
"""trans 子命令冒烟测试（不调用 API）。

覆盖：模块导入链、关键纯函数、OpenAIClient.from_args 参数映射。
端到端翻译（pandoc + GPT API）不在本测试范围。
"""

import os
import tempfile
from argparse import Namespace
from typing import List

import pytest


def test_import_chain():
    import BookerEpubTool.trans
    import BookerEpubTool.trans_agent
    import BookerEpubTool.trans_models
    import BookerEpubTool.trans_pmt
    import BookerEpubTool.resplit_agent
    import BookerEpubTool.resplit_models
    import BookerEpubTool.resplit_pmt
    import BookerEpubTool.clean_heading
    import BookerEpubTool.openai
    import BookerEpubTool.tomd
    import BookerEpubTool.fmt
    import BookerEpubTool.util
    assert BookerEpubTool.trans.TransDispatcher is not None


def test_tomd_bold():
    from BookerEpubTool.tomd import tomd
    assert '**hi**' in tomd('<p><strong>hi</strong></p>')


def test_tomd_superscript():
    from BookerEpubTool.tomd import tomd
    assert 'a²' in tomd('<p>a<sup>2</sup></p>')


def test_fmt_zh():
    from BookerEpubTool.fmt import fmt_zh
    # 与源项目 BookerGptTool.fmt.fmt_zh 行为一致：
    # fmt_en_zh_gap 仅在字母数字与汉字之间加空格，标点两侧不加
    assert fmt_zh('在Python中list.append()方法') == '在 Python 中 list.append()方法'


def test_fmt_publisher_none():
    from BookerEpubTool.fmt import fmt_publisher
    text = '<p>hello</p>'
    assert fmt_publisher(text, 'none') == text


def test_to_kebab():
    from BookerEpubTool.util import to_kebab
    assert to_kebab('Deep Learning with Python') == 'deep-learning-with-python'


def test_split_md_lines_group_chunks():
    from BookerEpubTool.util import split_md_lines, group_chunks
    md = '# Title\n\nsome para\n\n```python\ncode\n```\n\nend\n'
    lines = split_md_lines(md)
    assert lines == ['# Title', 'some para', '```python\ncode\n```', 'end']
    groups = group_chunks(lines, limit=8000)
    assert len(groups) == 1 and 'end' in groups[0]


def test_yaml_model_roundtrip(tmp_path):
    from BookerEpubTool.trans_models import Chunk
    from BookerEpubTool.util import write_yaml_model, read_yaml_model
    fname = str(tmp_path / 'chunks.yaml')
    chunks = [Chunk(raw='a'), Chunk(raw='b')]
    write_yaml_model(fname, chunks)
    back = read_yaml_model(fname, List[Chunk])
    assert back is not None
    assert [c.raw for c in back] == ['a', 'b']


def test_text_roundtrip(tmp_path):
    from BookerEpubTool.util import write_text, read_text
    fname = str(tmp_path / 'sub' / 'x.md')
    write_text(fname, 'hello\n')
    assert read_text(fname) == 'hello\n'


def test_openai_client_from_args():
    from BookerEpubTool.openai import OpenAIClient
    ns = Namespace(
        key='k', host='http://127.0.0.1', user_agent='u',
        stream=False, read_timeout=1, conn_timeout=1,
        repetition_regex='', no_think=False,
    )
    c = OpenAIClient.from_args(ns)
    assert c.api_key == 'k'
    assert c.base_url == 'http://127.0.0.1'
    assert c.user_agent == 'u'