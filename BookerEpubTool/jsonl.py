import os
from os import path
import json
import subprocess as subp
import py7zr
from io import BytesIO
from .util import *

def get_paras(html, ch=0):
    html = rm_xml_header(html)
    rt = pq(html)
    els = rt('p, h1, h2, h3, h4, h5, h6')
    paras = []
    for i, el in enumerate(els):
        para = (pq(el).text() or '').strip()
        lv = 0 if el.tag == 'p' else int(el.tag[1])
        paras.append({
            'chapter': ch,
            'paragraph': i,
            'content': para,
            'level': lv,
        })
    return paras

def to_jsonl(args):
    fname = args.fname
    if not path.isfile(fname) or \
        not fname.endswith('.epub'):
        print('请提供 EPUB 文件')
        return
    print(fname)
    fdict = read_zip(fname)
    opf, _ = read_opf_ncx(fdict)
    fnames = get_opf_text_fnames(opf)
    jsons = []
    for i, f in enumerate(fnames):
        html = fdict[f].decode('utf8')
        paras = get_paras(html, i)
        jsons.append(paras)
    jsonl = '\n'.join(
        json.dumps(j, ensure_ascii=False).replace('\n', ' ') 
        for j in jsons
    )
    jsonl_fname = path.basename(fname)[:-5] + '.jsonl'
    bio = BytesIO()
    zip = py7zr.SevenZipFile(bio, 'w', filters=[{'id': py7zr.FILTER_LZMA2}])
    zip.writestr(jsonl, jsonl_fname)
    zip.close()
    data = bio.getvalue()
    # cmd = ['7z', 'a', '-mx9', ofname + '.7z', ofname]
    # subp.Popen(cmd, shell=True).communicate()
    ofname = fname[:-5] + '.jsonl.7z'
    open(ofname, 'wb').write(data)
    print(ofname)
    
def get_title_paras(html):
    rt = pq(html)
    title = (rt('h1').text() or '').strip()
    paras = [
        pq(el).text().strip()
        for el in rt('p')
    ]
    return {'title': title, 'paras': paras}
    
def chs2yaml(args):
    fname = args.fname
    if not path.isfile(fname) or \
        not fname.endswith('.epub'):
        print('请提供 EPUB 文件')
        return
    print(fname)
    fdict = read_zip(fname)
    opf, _ = read_opf_ncx(fdict)
    fnames = get_opf_text_fnames(opf)
    htmls = [
        fdict[fname].decode('utf8')
        for fname in fnames
    ]
    chs = [
        get_title_paras(html)
        for html in htmls
    ]
    res = {
        'title': chs[0]['title'],
        'paras': chs[1:],
    }
    ofname = fname[:-5] + '.yaml'
    open(ofname, 'wb').write(yaml.safe_dump(res, allow_unicode=True))
    print(ofname)
    
