import os
from os import path
import json
import subprocess as subp
from .util import *

def get_paras(html):
    html = rm_xml_header(html)
    rt = pq(html)
    els = rt('p, h1, h2, h3, h4, h5, h6')
    paras = []
    for el in els:
        para = (pq(el).text() or '').strip()
        paras.append(para)
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
        paras = get_paras(html)
        paras = [{
            'content': p,
            'chapter': i, 
            "paragraph": j
        } for j, p in enumerate(paras)]
        jsonl.append(paras)
    jsonl = '\n'.join(
        json.dumps(j, ensure_ascii=False).replace('\n', ' ') 
        for j in jsons
    )
    ofname = fname[:-5] + '.jsonl'
    open(ofname, 'w', encoding='utf8').write(jsonl)
    cmd = ['7z', 'a', '-mx9', ofname + '.7z', ofname]
    subp.Popen(cmd, shell=True).communicate()
    os.unlink(ofname)