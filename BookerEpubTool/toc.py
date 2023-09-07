from os import path
from imgyaso import pngquant_bts
import sys
from EpubCrawler.util import is_pic, safe_mkdir, safe_rmdir
import subprocess as subp
from pyquery import PyQuery as pq
import re
from .util import *

def get_opf_flist(opf):
    refs = opf['refs']
    id_map = opf['items']
    return [
        id_map[id]
        for id in refs
        if id in id_map
    ]


def get_ncx_toc(toc_ncx, rgx="", hlv=0):
    toc_ncx = re.sub(r'<\?xml[^>]*\?>', '', toc_ncx)
    toc_ncx = re.sub(r'(?<=<)ncx:', '', toc_ncx)
    toc_ncx = re.sub(r'(?<=</)ncx:', '', toc_ncx)
    toc_ncx = re.sub(r'xmlns=".+?"', '', toc_ncx)
    toc_ncx = re.sub(r'<(/?)navLabel', r'<\1label', toc_ncx)
    toc_ncx = re.sub(r'<(/?)navPoint', r'<\1nav', toc_ncx)
    toc_ncx = re.sub(r'<(/?)navmap', r'<\1map', toc_ncx)
    rt = pq(toc_ncx)
    el_nps = rt('nav')
    toc = []
    for i in range(len(el_nps)):
        el = el_nps.eq(i)
        title = el.children('label>text').text()
        src = el.children('content').attr('src')
        toc.append({
            'idx': i,
            'title': title.strip(),
            'src': src,
            'level': get_toc_lv(el),
        })
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

def get_toc_and_content_path(fdict):
    meta_path = 'META-INF/container.xml'
    if meta_path not in fdict:
        return (None, None)
    meta = fdict[meta_path].decode('utf-8')
    meta = re.sub(r'<\?xml[^>]*\?>', '', meta)
    meta = re.sub(r'xmlns=".+?"', '', meta)
    opf_path = pq(meta).find('rootfile').attr('full-path') or ''
    if opf_path not in fdict:
        return (None, None)
    opf = fdict[opf_path].decode('utf-8')
    opf = re.sub(r'<\?xml[^>]*\?>', '', opf)
    opf = re.sub(r'xmlns=".+?"', '', opf)
    ncx_path = pq(opf).find('item#ncx').attr('href') or ''
    ncx_path = path.join(path.dirname(opf_path), ncx_path).replace('\\', '/')
    if ncx_path not in fdict:
        return (None, None)
    return (ncx_path, opf_path)
            

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
    flist = get_opf_flist(opf)
    toc_flist = {
        re.sub(r'#.+$|\?.+$', '', ch['src']) 
        for ch in toc
    }
    # 按照目录合并文件
    chs = []
    for f in flist:
        cont = fdict[f].decode('utf8')
        cont = get_html_body(cont)
        if f in toc_flist:
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
        fname = path.join(dir, str(i).zfill(l) + '.html')
        open(fname, 'w', encoding='utf8').write(ch)
        