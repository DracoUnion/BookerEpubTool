# -*- coding: utf-8 -*-

from pydantic import BaseModel, Field
from typing import *

class AnchorLink(BaseModel):
    """网页中的一个候选链接"""
    no: int = Field(..., description='候选链接编号')
    text: str = Field(..., description='链接文字')
    href: str = Field(..., description='链接地址')

class TocItem(BaseModel):
    """目录中的一个章节链接"""
    no: int = Field(..., description='章节序号（保持目录顺序）')
    title: str = Field(..., description='章节标题')
    href: str = Field('', description='章节链接地址，无链接时为空字符串')

class ArticleResult(BaseModel):
    """从章节网页中提取的正文"""
    title: str = Field(..., description='章节标题')
    content: str = Field(..., description='章节正文的 HTML 片段')