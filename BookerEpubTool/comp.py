from os import path
from imgyaso import pngquant_bts
import sys
from EpubCrawler.util import is_pic, safe_mkdir, safe_rmdir
import subprocess as subp
from pyquery import PyQuery as pq
import re
from .util import *

def compress(args):
    fname = args.file
    if fname.endswith('.mobi') or \
        fname.endswith('.azw3'):
            fname = convert_to_epub(fname)
    elif not fname.endswith('.epub'):
        print('请提供EPUB')
        return
        
    fdict = read_zip(fname)
    for name, data in fdict.items():
        print(name)
        if is_pic(name):
            data = pngquant_bts(data)
            

        
    write_zip(fname, fdict)
    print('done...')