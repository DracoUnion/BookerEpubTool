from os import path
from imgyaso import pngquant_bts
import sys
from EpubCrawler.util import is_pic, safe_mkdir, safe_rmdir
import subprocess as subp
from pyquery import PyQuery as pq
import re
from .util import *
import os
import shutil

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

    # 处理 ALLINONE 逻辑
    if args.all_in_one:
        cont = '\n'.join([
            get_html_body(fdict[f].decode('utf8'))
            for f in get_opf_text_fnames(opf)
        ])
        cont = f'<html><head></head><body>{cont}</body></html>' 
        ofname = args.fname[:-5] + '.html'
        print(ofname)
        open(ofname, 'w', encoding='utf8').write(cont)
        return

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
        

def ext_htmls(args):
    fname = args.fname
    if not fname.endswith('.epub'):
        print('请提供 EPUB 文件')
        return

    # 获取目录和文件列表
    fdict = read_zip(fname)
    htmls = {
        path.basename(name):data
        for name, data in fdict.items()
        if extname(name) in ['html', 'htm', 'xhtml']
    }

    for name, data in htmls.items():
        name = re.sub(r'\.\w+$', '', name) + '.html'
        print(name)
        fname = path.join(args.output_dir, args.prefix + name)
        open(fname, 'wb').write(data)
    

def ext_pics(args):
    fname = args.fname
    if not fname.endswith('.epub'):
        print('请提供 EPUB 文件')
        return

    # 获取目录和文件列表
    fdict = read_zip(fname)
    pics = {
        path.basename(name):data
        for name, data in fdict.items()
        if is_pic(name)
    }

    for name, data in pics.items():
        print(name)
        fname = path.join(args.output_dir, args.prefix + name)
        open(fname, 'wb').write(data)

def select_nocode(args):
    fname = args.fname
    if not fname.endswith('.epub'):
        print('请提供 EPUB 文件')
        return

    # 获取目录和文件列表
    fdict = read_zip(fname)
    htmls = {
        path.basename(name):data
        for name, data in fdict.items()
        if extname(name) in ['html', 'htm', 'xhtml']
    }
    nocode = all(
        '</code>' not in data.decode('utf8', 'ignore') 
        for data in htmls.values()
    )
    if nocode:
        shutil.move(
            args.fname,
            path.join(args.output_dir, path.basename(args.fname))
        )

def reg_subparser(subparsers):
    toc_parser = subparsers.add_parser("toc", help="查看 EPUB 目录")
    toc_parser.add_argument("fname", help="文件")
    toc_parser.add_argument("-l", "--hlevel", default=0, type=int, help="目录层级上限，仅显示级别 ≤ 该值的条目；0 表示全部")
    toc_parser.add_argument("-r", "--regex", help="章节标题正则，仅显示匹配的条目")
    toc_parser.set_defaults(func=get_toc)

    chs_parser = subparsers.add_parser("ext-chs", help="导出 EPUB 章节")
    chs_parser.add_argument("fname", help="文件")
    chs_parser.add_argument("-d", "--dir", default='.', help="输出目录")
    chs_parser.add_argument("-s", "--start", default=-1, type=int, help="起始章节下标；-1 表示全部")
    chs_parser.add_argument("-e", "--end", default=-1, type=int, help="结束章节下标；-1 表示全部")
    chs_parser.add_argument("-l", "--hlevel", default=0, type=int, help="目录层级上限，用于判定章节边界；0 表示全部")
    chs_parser.add_argument("-r", "--regex", help="章节标题正则，用于判定章节边界")
    chs_parser.add_argument("-p", "--prefix", default='', help="输出文件前缀")
    chs_parser.add_argument("-a", "--all-in-one", action='store_true', help="是否合并为一个 HTML")
    chs_parser.set_defaults(func=ext_chs)

    ext_htmls_parser = subparsers.add_parser("ext-htmls", help="导出 EPUB 的 HTML 文件")
    ext_htmls_parser.add_argument("fname", help="文件")
    ext_htmls_parser.add_argument("-o", '--output-dir', default='.', help="输出目录")
    ext_htmls_parser.add_argument("-p", '--prefix', default='', help="输出文件前缀")
    ext_htmls_parser.set_defaults(func=ext_htmls)

    ext_pics_parser = subparsers.add_parser("ext-pics", help="导出 EPUB 的图片")
    ext_pics_parser.add_argument("fname", help="文件")
    ext_pics_parser.add_argument("-o", '--output-dir', default='.', help="输出目录")
    ext_pics_parser.add_argument("-p", '--prefix', default='', help="输出文件前缀")
    ext_pics_parser.set_defaults(func=ext_pics)

    sel_nocd_parser = subparsers.add_parser("sel-nocd", help="筛选不含代码的 EPUB")
    sel_nocd_parser.add_argument("fname", help="文件")
    sel_nocd_parser.add_argument("-o", '--output-dir', default='.', help="输出目录")
    sel_nocd_parser.set_defaults(func=select_nocode)
