import zipfile
from io import BytesIO
import re
import subprocess as subp
from os import path
from pyquery import PyQuery as pq

def read_zip(fname):
    bio = BytesIO(open(fname, 'rb').read())
    zip = zipfile.ZipFile(bio, 'r')
    fdict = {n:zip.read(n) for n in zip.namelist()}
    zip.close()
    return fdict

def write_zip(fname, fdict):
    bio = BytesIO()
    zip = zipfile.ZipFile(bio, 'w', zipfile.ZIP_DEFLATED)
    for name, data in fdict.items():
        zip.writestr(name, data)
    zip.close()
    open(fname, 'wb').write(bio.getvalue())

def convert_to_epub(fname):
    nfname = re.sub(r'\.\w+$', '', fname) + '.epub'
    print(f'{fname} => {nfname}')
    subp.Popen(f'ebook-convert "{fname}" "{nfname}"', 
        shell=True, stdin=subp.PIPE, stdout=subp.PIPE).communicate()
    if not path.exists(nfname):
        raise FileNotFoundError(f'{nfname} not found')
    return nfname

def rm_xml_header(html):
    html = re.sub(r'<\?xml[^>]*\?>', '', html)
    html = re.sub(r'xmlns(:\w+)?=".+?"', '', html)
    html = re.sub(r'</?\w+', lambda m: m.group().lower(), html)
    return html

def parse_opf(opf, base):
    opf = rm_xml_header(opf)
    rt = pq(opf)
    
    el_meta = rt.find('metadata')
    meta = {}
    for el in el_meta.children():
        el = pq(el)
        tagname = el[0].tag
        if tagname == 'meta':
            name, content = el.attr('name'), el.attr('content')
            if name and content:
                meta[name] = content
        else:
            meta[tagname] = el.text() or ''
    
    el_assets = rt.find('item')
    items = {}
    for el in el_assets:
        el = pq(el)
        id_, href = el.attr('id'), el.attr('href')
        if id_ and href:
            items[id_] = path.join(base, href).replace('\\', '/')
    if 'ncxtoc' in items:
        items['ncx'] = items['ncxtoc']
        del items['ncx']
    
    refs = []
    el_refs = rt.find('itemref')
    for el in el_refs:
        idref = pq(el).attr('idref')
        if idref: refs.append(idref)
    return {
        'meta': meta,
        'items': items,
        'refs': refs,
    }

def parse_ncx(ncx, base):
    ncx = ncx.replace('ncx:', '')
    ncx = rm_xml_header(ncx)
    rt = pq(ncx)

    el_metas = rt('head>meta')
    meta = {}
    for el in el_metas:
        el = pq(el)
        name, content = el.attr('name'), el.attr('content')
        if name and content:
            meta[name] = content
    el_title = rt('doctitle>text')
    title = el_title.text() or ''

    nav = []
    el_navpts = rt('navpoint')
    for el in el_navpts:
        el = pq(el)
        id_, order = el.attr('id'), el.attr('playOrder')
        if not (id_ and order): continue
        el_text, el_cont = el.find('navlabel>text'), el.find('content')
        if not (len(el_text) and len(el_cont)): 
            continue
        text, src = el_text.text(), el_cont.attr('src')
        if not (text and src): continue
        el_parent = el.parent()
        parent_id = el_parent.attr('id')  \
                    if el_parent.is_('navpoint') else ''
        nav.append({
            'id': id_,
            'parent': parent_id,
            'order': int(order),
            'title': text.strip(),
            'src': path.join(base, src).replace('\\', '/'),
            'level': get_nav_lv(el),
        })
    nav.sort(key=lambda it: it['order'])

    return {
        'meta': meta,
        'title': title,
        'nav': nav
    }


def get_nav_lv(el_nav):
    cnt = 0
    while el_nav and el_nav.is_('navpoint'):
        cnt += 1
        el_nav = el_nav.parent()
    return cnt

def read_opf_ncx(fdict):
    meta_path = 'META-INF/container.xml'
    if meta_path not in fdict:
        raise ValueError(f'找不到 META 文件 [{meta_path}]') 
    meta = rm_xml_header(fdict[meta_path].decode('utf-8'))
    opf_path = pq(meta).find('rootfile').attr('full-path') or ''
    if not opf_path:
        raise ValueError(f'无法获取 OPF 文件路径')
    if opf_path not in fdict:
        raise ValueError(f'找不到 OPF 文件 [{opf_path}]')
    opf = fdict[opf_path].decode('utf-8')
    opf = parse_opf(opf, path.dirname(opf_path))
    if 'ncx' not in opf['items']:
        raise ValueError('无法获取 NCX 文件路径')
    ncx_path = opf['items']['ncx']
    if ncx_path not in fdict:
        raise ValueError(f'找不到 NCX 文件 [{ncx_path}]')
    ncx = fdict[ncx_path].decode('utf8')
    ncx = parse_ncx(ncx, path.dirname(ncx_path))
    return (opf, ncx)

def get_opf_text_fnames(opf):
    refs = opf['refs']
    id_map = opf['items']
    return [
        id_map[id]
        for id in refs
        if id in id_map
    ]