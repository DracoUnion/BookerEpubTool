import re
from pyquery import PyQuery as pq
from .util import *

def format_para(args):
    fname = args.fname
    lo = args.low
    hi = args.high
    if not fname.endswith('.epub'):
        print('请提供EPUB')
        return

    fdict = read_zip(fname)
    for n, data in fdict.items():
        print(n)
        if n.endswith('.html'):
            data = format_para_html(
                data.decode('utf8'), lo, hi).encode('utf8')
        
    write_zip(fname, fdict)
    print('done...')

def format_para_html(html, lo, hi):
    html = re.sub(r'<\?xml[^>]*\?>', '', html)
    rt = pq(html)
    el_ps = rt('p')
    for el in el_ps:
        el = pq(el)
        if el.children().is_('img'): continue
        if not el.next().is_('p'): continue
        cont = (el.text() or '').trim()
        if lo <= len(cont) <= hi and \
           not re.search(r'[。！？：”]$', cont):
            el.add_class('can_merge')
    
    for el in el_ps:
        el = pq(el)
        if not el.has_class('can_merge'):
            continue
        cont = (el.html() or '') + (el.next().html() or '')
        el.next().html(cont)
        el.remove()
    return str(rt)

def reg_subparser(subparsers):
    fmt_para_parser = subparsers.add_parser("fmt-para", help="格式化 EPUB 段落")
    fmt_para_parser.add_argument("fname", help="文件")
    fmt_para_parser.add_argument("-l", "--low", type=int, default=30, help="触发合并的段落长度下界")
    fmt_para_parser.add_argument("-u", "--high", type=int, default=35, help="触发合并的段落长度上界")
    fmt_para_parser.set_defaults(func=format_para)