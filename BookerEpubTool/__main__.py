#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-

import argparse
from . import __version__

def main():
    parser = argparse.ArgumentParser(prog="BookerEpubTool", description="iBooker EPUB tool", formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--version", action="version", version=f"BookerEpubTool version: {__version__}")
    parser.set_defaults(func=lambda x: parser.print_help())
    subparsers = parser.add_subparsers()

    from .comp import reg_subparser as reg_comp
    from .toc import reg_subparser as reg_toc
    from .fmt import reg_subparser as reg_fmt
    from .mkds import reg_subparser as reg_mkds
    from .title import reg_subparser as reg_title

    reg_comp(subparsers)
    reg_toc(subparsers)
    reg_fmt(subparsers)
    reg_mkds(subparsers)
    reg_title(subparsers)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__": main()