from os import path
from imgyaso import pngquant_bts
import sys
from EpubCrawler.util import is_pic, safe_mkdir, safe_rmdir
import subprocess as subp
from pyquery import PyQuery as pq
import re
from .util import *

def filter_toc(toc, rgx, hlv):
    for i, ch in enumerate(toc):
        ch['idx'] = i
    if rgx:
        toc = [
            ch for ch in toc 
            if re.search(rgx, ch['title'])
        ]
    if hlv:
        toc = [
            ch for ch in toc 
            if ch['level'] <= hlv
        ]
    return toc
def get_toc(args):
    fname = args.fname
    if not fname.endswith('.epub'):
        print('请提供 EPUB 文件')
        return
        
    fdict = read_zip(fname)
    _, ncx = read_opf_ncx(fdict)
    toc = filter_toc(ncx['nav'], args.regex, args.hlevel)
    for i, ch in enumerate(toc):
        pref = '>' * (ch["level"] - 1)
        if pref: pref += ' '
        print(f'{pref}{i}-{ch["idx"]}：{ch["src"]}\n{pref}{ch["title"]}')

def get_html_body(html):
    html = rm_xml_header(html)
    rt = pq(html)
    return rt('body').html() if rt('body') else html

def ext_chs(args):
    fname = args.fname
    rgx = args.regex
    hlv = args.hlevel
    st = int(args.start)
    if st == -1: st = 0
    ed = int(args.end)
    if ed == -1: ed = 2 ** 32
    dir = args.dir
    
    if not fname.endswith('.epub'):
        print('请提供 EPUB 文件')
        return

    # 获取目录和文件列表
    fdict = read_zip(fname)
    opf, ncx = read_opf_ncx(fdict)
    toc = filter_toc(ncx['nav'], args.regex, args.hlevel)
    fnames = get_opf_text_fnames(opf)
    toc_fnames = {
        re.sub(r'#.+$|\?.+$', '', ch['src']) 
        for ch in toc
    }
    # 按照目录合并文件
    chs = []
    for f in fnames:
        cont = fdict[f].decode('utf8')
        cont = get_html_body(cont)
        if f in toc_fnames:
            chs.append([cont])
        else:
            if chs: chs[-1].append(cont)
    chs = chs[st:ed+1]
    chs = ['\n'.join(ch) for ch in chs]
    chs = [
        f'<html><head></head><body>{ch}</body></html>' 
        for ch in chs
    ]
    l = len(str(len(chs)))
    for i, ch in enumerate(chs):
        fname = path.join(dir, args.prefix + str(i).zfill(l) + '.html')
        open(fname, 'w', encoding='utf8').write(ch)
        