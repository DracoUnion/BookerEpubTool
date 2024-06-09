#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-

import argparse
import requests
from readability import Document
import tempfile
import uuid
import subprocess as subp
import re
import os
import json
import yaml
from urllib.parse import quote_plus
from os import path
from pyquery import PyQuery as pq
from datetime import datetime
from collections import OrderedDict
from EpubCrawler.img import process_img
from EpubCrawler.util import safe_mkdir
from . import __version__
from .util import *
from .fmt import *
from .comp import *
from .toc import *
from .mkds import *
from .title import *
    
def main():
    parser = argparse.ArgumentParser(prog="BookerEpubTool", description="iBooker EPUB tool", formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--version", action="version", version=f"BookerEpubTool version: {__version__}")
    parser.set_defaults(func=lambda x: parser.print_help())
    subparsers = parser.add_subparsers()
    
    
    


    comp_parser = subparsers.add_parser("comp", help="compress epub")
    comp_parser.add_argument("file", help="file")
    comp_parser.add_argument("-m", "--mode", default='quant', help="mode")
    comp_parser.add_argument("-c", "--color", type=int, default=8, help="num of colors")
    comp_parser.set_defaults(func=compress)

    toc_parser = subparsers.add_parser("toc", help="view epub toc")
    toc_parser.add_argument("fname", help="fname")
    toc_parser.add_argument("-l", "--hlevel", default=0, type=int, help="heading level, headings less than which will be revserved. 0 means all")
    toc_parser.add_argument("-r", "--regex", help="regex for chapter title")
    toc_parser.set_defaults(func=get_toc)

    chs_parser = subparsers.add_parser("ext-chs", help="export epub chapters")
    chs_parser.add_argument("fname", help="fname")
    chs_parser.add_argument("-d", "--dir", default='.', help="output dir")
    chs_parser.add_argument("-s", "--start", default=-1, type=int, help="starting index. -1 means all")
    chs_parser.add_argument("-e", "--end", default=-1, type=int, help="ending index. -1 means all")
    chs_parser.add_argument("-l", "--hlevel", default=0, type=int, help="heading level, headings less than which will be revserved. 0 means all")
    chs_parser.add_argument("-r", "--regex", help="regex for chapter title")
    chs_parser.add_argument("-p", "--prefix", default='', help="prefix")
    chs_parser.set_defaults(func=ext_chs)

    fmt_para_parser = subparsers.add_parser("fmt-para", help="format epub paragraphs")
    fmt_para_parser.add_argument("fname", help="file name")
    fmt_para_parser.add_argument("-l", "--low", type=int, default=30, help="lower bound")
    fmt_para_parser.add_argument("-u", "--high", type=int, default=35, help="upper bound")
    fmt_para_parser.set_defaults(func=format_para)

    chs2yaml_parser = subparsers.add_parser("mkds", help="epub paragraphs to yaml dataset")
    chs2yaml_parser.add_argument("fname", help="file name")
    chs2yaml_parser.add_argument("-t", "--title", default='h1', help="css selector for title")
    chs2yaml_parser.add_argument("-p", "--paras", default='p', help="css selector for paragraphs")
    chs2yaml_parser.add_argument("-w", "--whole", action='store_true', help="whether to parse body entirely as paragraphs")
    chs2yaml_parser.set_defaults(func=make_dataset)

    add_title_parser = subparsers.add_parser("add-title", help="add title to epub")
    add_title_parser.add_argument("fname", help="file name")
    add_title_parser.set_defaults(func=add_title)

    ext_htmls_parser = subparsers.add_parser("ext-htmls", help="add title to epub")
    ext_htmls_parser.add_argument("fname", help="file name")
    ext_htmls_parser.add_argument("-o", '--output-dir', default='.', help="output dir")
    ext_htmls_parser.add_argument("-p", '--prefix', default='', help="prefix")
    ext_htmls_parser.set_defaults(func=ext_htmls)

    ext_pics_parser = subparsers.add_parser("ext-pics", help="add title to epub")
    ext_pics_parser.add_argument("fname", help="file name")
    ext_pics_parser.add_argument("-o", '--output-dir', default='.', help="output dir")
    ext_pics_parser.set_defaults(func=ext_pics)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__": main()