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
    ofname = fname[:-5] + '.jsonl'
    open(ofname, 'w', encoding='utf8').write(jsonl)
    bio = BytesIO()
    zip = py7zr.SevenZipFile(bio, 'w', filters=[{'id': py7zr.FILTER_LZMA2}])
    zip.write(ofname, path.basename(ofname))
    zip.close()
    data = bio.getvalue()
    # cmd = ['7z', 'a', '-mx9', ofname + '.7z', ofname]
    # subp.Popen(cmd, shell=True).communicate()
    os.unlink(ofname)
    open(ofname + '.7z', 'wb').write(data)
