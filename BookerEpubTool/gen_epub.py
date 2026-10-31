#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-

"""GenEpub
https://github.com/apachecn/gen-epub"""

import zipfile
import uuid
import re
from os import path
import jinja2
from datetime import datetime
from io import BytesIO
from .util import *

__author__ = "wizardforcel"
__email__ = "wizard.z@qq.com"
__license__ = "SATA"
__version__ = "2023.7.9.0"

def gen_epub_aio(articles, imgs=None, name=None, path=None):
    imgs = imgs or {}
    name = name or articles[0]['title']
    path = path or fname_escape(name) + '.epub'
    if not path.endswith('.epub'):
        path += '.epub'
        
    mimetype = open(d('./assets/mimetype'), 'rb').read()
    container  = open(d('./assets/container.xml'), 'rb').read()
    style = open(d('./assets/Style.css'), 'rb').read()
    articleTemp = open(d('./assets/article.j2'), encoding='utf-8').read()
    contentTemp = open(d('./assets/content.j2'), encoding='utf-8').read()
    tocTemp = open(d('./assets/toc.j2'), encoding='utf-8').read()
    
    bio = BytesIO()
    zip = zipfile.ZipFile(bio, 'w', zipfile.ZIP_DEFLATED)
    zip.writestr('mimetype', mimetype)
    zip.writestr('META-INF/container.xml', container)
    zip.writestr('OEBPS/Styles/Style.css', style)
    
    l = len(str(len(articles)))
    articleTemp = jinja2.Template(articleTemp)
    for i, art in enumerate(articles):
        pad_num = str(i).zfill(l)
        zip.writestr(f'OEBPS/Text/{pad_num}.html', 
            articleTemp.render(**art).encode('utf-8'))
        
    for fname, img in imgs.items():
        zip.writestr(f'OEBPS/Images/{fname}', img)
        
    uuid_ = uuid.uuid4().hex
    html_toc = [
        {
            'title': art['title'],
            'file': str(i).zfill(l) + '.html',
        } 
        for i, art in enumerate(articles)
    ]
    img_toc = [
        {'file': fname}
        for fname in imgs
    ]
    
    co = jinja2.Template(contentTemp) \
        .render(
            date=datetime.now().strftime('%Y-%m-%d'),
            img_toc=img_toc,
            html_toc=html_toc,
            uuid=uuid_,
            name=name,
        )
    zip.writestr('OEBPS/content.opf', co.encode('utf-8'))
    
    toc = jinja2.Template(tocTemp) \
        .render(toc=html_toc, uuid=uuid_)
    zip.writestr('OEBPS/toc.ncx', toc.encode('utf-8'))
    
    zip.close()
    data = bio.getvalue()
    open(path, 'wb').write(data)
    
def gen_epub_paging(articles, imgs=None, name=None, path=None, limit='50m'):
    imgs = imgs or {}
    name = name or articles[0]['title']
    path = path or fname_escape(name) + '.epub'
    if not path.endswith('.epub'):
        path += '.epub'
        
    total = sum(len(v) for _, v in imgs.items()) + \
            sum(
                comp_size(a['title'] + a['content'])
                for a in articles
            )
    limit = size_str_to_int(limit)
    if total <= limit:
        gen_epub_aio(articles, imgs, name, path)
        return

    art_part = []
    img_part = {}
    total = 0
    ipt = 1
    for a in articles:
        art_imgs = re.findall(r'src="\.\./Images/(\w{32}\.png)"', a['content'])
        size = sum(
            len(imgs.get(iname, b'')) 
            for iname in art_imgs
        ) + comp_size(a['title'] + a['content'])
        if total + size >= limit:
            art_part.insert(0, {
                'title': f'{name} PT{ipt}',
                'content': "",
            })
            gen_epub_aio(art_part, img_part)
            art_part = []
            img_part = {}
            total = 0
            ipt += 1
        art_part.append(a)
        img_part.update({
            iname:imgs.get(iname, b'') 
            for iname in art_imgs
        })
        total += size
    if art_part:
        art_part.insert(0, {
            'title': f'{name} PT{ipt}',
            'content': "",
        })
        gen_epub_aio(art_part, img_part)

gen_epub = gen_epub_paging

