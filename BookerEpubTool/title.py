from .util import *
from pyquery import PyQuery as pq

def add_title(args):
    if not args.fname.endswith('.epub'):
        print('请提供 EPUB 文件')
        return

    fdict = read_zip(args.fname)
    _, ncx = read_opf_ncx(fdict)
    for it in ncx['nav']:
        title, src = it['title'], it['src']
        html = fdict[src].decode('utf8', 'ignore')
        rt = pq(rm_xml_header(html))
        if not rt.find('body').children().eq(0).is_('h1, h2, h3'):
            el = pq('<h1></h1>')
            el.text(title)
            rt.find('body').prepend(el)
            html = str(rt)
            fdict[src] = html.encode('utf8')

    write_zip(args.fname, fdict)
