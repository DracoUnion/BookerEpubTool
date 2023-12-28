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
from .jsonl import *
    
def main():
    parser = argparse.ArgumentParser(prog="BookerEpubTool", description="iBooker EPUB tool", formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--version", action="version", version=f"BookerEpubTool version: {__version__}")
    parser.set_defaults(func=lambda x: parser.print_help())
    subparsers = parser.add_subparsers()
    
    
    


    comp_parser = subparsers.add_parser("comp", help="compress epub")
    comp_parser.add_argument("file", help="file")
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

    jsonl_parser = subparsers.add_parser("tojsonl", help="epub paragraphs to jsonl dataset")
    jsonl_parser.add_argument("fname", help="file name")
    jsonl_parser.set_defaults(func=to_jsonl)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__": main()