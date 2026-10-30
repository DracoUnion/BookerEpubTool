import requests
import zipfile
from io import BytesIO
import re
import subprocess as subp
from os import path
import os
import sys
import hashlib
import ctypes
import tempfile
import uuid
import yaml
import json
from pyquery import PyQuery as pq
from typing import *
from pydantic import BaseModel, parse_obj_as, ValidationError

FDict = Dict[str, bytes]
OpfDict = Dict[str, Any]
NcxDict = Dict[str, Any]

def read_zip(fname: str) -> FDict:
    bio = BytesIO(open(fname, 'rb').read())
    zip = zipfile.ZipFile(bio, 'r')
    fdict = {n:zip.read(n) for n in zip.namelist()}
    zip.close()
    return fdict

def write_zip(fname: str, fdict: FDict):
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

def rm_xml_header(html: str) -> str:
    html = re.sub(r'<\?xml[^>]*\?>', '', html)
    html = re.sub(r'xmlns(:\w+)?=".+?"', '', html)
    html = re.sub(r'</?\w+', lambda m: m.group().lower(), html)
    return html

def parse_opf(opf: str, base: str) -> OpfDict:
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
        del items['ncxtoc']
    if 'ncx' not in items and \
       'OEBPS/toc.ncx' in items.values():
        items['ncx'] = 'OEBPS/toc.ncx'
    
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

def parse_ncx(ncx: str, base: str) -> NcxDict:
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
        el_text = el.children('navlabel').children('text')
        el_cont = el.children('content')
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
            'order': int(order, 16),
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

def read_opf_ncx(fdict: Dict[str, bytes]) -> Tuple[OpfDict, NcxDict]:
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

def extname(fname):
    m = re.search(r'\.(\w+)$', fname.lower())
    return m.group(1) if m else ''

# ── GPT 翻译相关工具（自 BookerGptTool 迁移）──────────────────────

def md5(text: str):
    return hashlib.md5(text.encode('utf8')).hexdigest()

def gen_objs_md5(*args):
    args = [
        o if isinstance(o, str) else
            json_dump_model(o)
        for o in args
    ]
    return '_'.join(md5(o) for o in args)

def get_md_title(text):
    RE_TITLE = r'^#+\x20+(.+?)$'
    m = re.search(RE_TITLE, text, flags=re.M)
    if not m:
        return None, (None, None)
    return m.group(1).strip(), m.span(1)

def epub2html_pandoc(epub):
    fname = path.join(tempfile.gettempdir(), uuid.uuid4().hex + '.epub')
    ofname = fname[:-5] + '.html'
    open(fname, 'wb').write(epub)
    subp.Popen(['pandoc', fname, '-o', ofname]).communicate()
    html = open(ofname, encoding='utf8').read()
    os.remove(fname)
    os.remove(ofname)
    return html

def to_kebab(name: str) -> str:
    """将技能名转为 kebab-case slug"""
    s = re.sub(r"[^\w\s一-鿿\-]", "", name)
    s = re.sub(r"[\s_]+", "-", s).strip("-").lower()
    return s[:60] or "unnamed"

def render_prompt(prompt: str, **kw):
    return re.sub(r"{(\w+)}", lambda g: kw.get(g.group(1), g.group(0)), prompt)

def group_chunks(chunks, limit=8000):
    groups = ['']
    for c in chunks:
        if len(groups[-1]) +  len(c) + 2 > limit:
            groups.append(c)
        else:
            groups[-1] += '\n\n' + c
    groups = [g for g in groups if g]
    return groups

def split_md_lines(md):
    lines = md.split('\n')
    res = []
    in_code = False
    code = ''
    for l in lines:
        if '```' in l:
            if in_code:
                # 结尾
                code += l
                res.append(code)
                code = ''
            else:
                # 开头
                code += l + '\n'
            in_code = not in_code
        elif not in_code:
            if l.strip(): res.append(l)
        elif in_code:
            code += l + '\n'
    # 处理结尾缺失情况：
    if code:
        res.append(code + '```')
    return res

ext_code_block = lambda s: re.search(r'```\w*([\s\S]+)```', s).group(1)
ext_cont_block = lambda s: re.search(r'\[content\]([\s\S]+)\[/content\]', s).group(1)

def malloc_trim_linux():
    if sys.platform == 'linux':
        libc = ctypes.CDLL("libc.so.6")
        libc.malloc_trim(0)

def json_dump_model(obj) -> str:
    """将对象（含 pydantic 模型/列表）序列化为 JSON 字符串。"""
    if isinstance(obj, BaseModel):
        obj = obj.model_dump()
    elif isinstance(obj, list):
        obj = [
            it.dict() if isinstance(it, BaseModel) else it
            for it in obj
        ]
    return json.dumps(obj, ensure_ascii=False)

def write_text(fname: str, text: str, append: bool = False) -> None:
    """将 text 以 UTF-8 写入 fname（自动创建父目录）。"""
    os.makedirs(path.dirname(fname), exist_ok=True)
    open(fname, 'a' if append else 'w', encoding='utf8').write(text)

def read_text(fname: str) -> str:
    """以 UTF-8 读取 fname 的文本内容。"""
    if not path.isfile(fname):
        return None
    text = open(fname, encoding='utf8').read()
    chs = set(text)
    # 避免读取损坏的数据
    if len(chs) == 1 and '\x00' in chs:
        text = ""
    return text

def write_yaml_model(fname: str, obj: Any) -> None:
    """将对象（含 pydantic 模型/列表）以 YAML 形式写入 fname。"""
    if isinstance(obj, BaseModel):
        obj = obj.dict()
    elif isinstance(obj, list):
        obj = [
            it.dict() if isinstance(it, BaseModel) else it
            for it in obj
        ]
    os.makedirs(path.dirname(fname), exist_ok=True)
    with open(fname, 'w', encoding='utf8') as f:
        yaml.safe_dump(obj, f, allow_unicode=True, sort_keys=False)

def read_yaml_model(fname: str, model: Optional[Type[BaseModel]]):
    """从 fname 读取 YAML 并解析为指定 pydantic 模型；文件缺失或损坏时返回 None。"""
    if not path.isfile(fname) or not path.getsize(fname):
        return None
    try:
        data = yaml.safe_load(open(fname, encoding='utf8').read())
        return parse_obj_as(model, data) if model else data
    except yaml.error.YAMLError:
        return None
    except ValidationError:
        return None

def request_retry(method, url, retry=10, check_status=False, **kw):
    kw.setdefault('timeout', 10)
    for i in range(retry):
        try:
            r = requests.request(method, url, **kw)
            if check_status: r.raise_for_status()
            return r
        except KeyboardInterrupt as e:
            raise e
        except Exception as e:
            print(f'{url} retry {i}')
            if i == retry - 1: raise e
