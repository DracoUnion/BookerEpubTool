import re
from pyquery import PyQuery as pq
from .util import *

def format_para_epub(args):
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
            data = format_para(
                data.decode('utf8'), lo, hi).encode('utf8')
        
    write_zip(fname, fdict)
    print('done...')

def format_para(html, lo, hi):
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