# -*- coding: utf-8 -*-

EXTRACT_TOC_PMT = '''
你是一个图书爬虫专家。下面是从网页中提取出的所有链接候选，每行格式为：

序号\t链接文字\t链接地址

例如：

3\t第1章 环境搭建\thttps://example.com/ch1.html

你的任务是从候选中筛选出“目录”中的章节链接。

## 要求

1. 只保留正文章节的链接，忽略导航、页脚、评论区、广告、上一页/下一页、目录页自身、作者介绍等无关链接。
2. 目录项按出现顺序输出（保持 no 升序）。
3. 若某目录项没有链接（例如只作为分隔标题），href 输出空字符串。
4. title 使用候选中的链接文字，可适当精简（去掉多余空白）。
5. 若网页没有目录，输出空数组 。
6. 严格按照 JSON 输出，包含在三个反引号（```）中。

## 输出格式

```
[
    {"no": 3, "title": "第1章 环境搭建", "href": "https://example.com/ch1.html"}
]
```

## 候选链接

{anchors}
'''


EXTRACT_ARTICLE_PMT = '''
你是一个图书爬虫专家。下面是从章节网页抓取的原始 HTML。

## 要求

1. title：输出章节标题，去除前后空白。
2. content：输出章节正文的 HTML 片段（保留 p、h1-h6、ul、ol、li、table、img、pre、code 等正文标签）。
3. 只输出正文本身，剔除导航、页脚、面包屑、评论、广告、侧边栏等无关元素。
4. 若正文里包含无效字符，或正文为空，content 输出空字符串。
5. 严格按照 JSON 输出，包含在三个反引号（```）中。

## 输出格式

```
{
    "title": "章节标题",
    "content": "<p>正文 HTML</p>"
}
```

## 章节网页 HTML

```html
{html}
```
'''

TRANS_HTML_PMT = '''
假设你是一个高级文档工程师和翻译员，请参考注意事项和示例，将给定英文 HTML 文本翻译成中文。

## 注意事项

-   粗体（<b>bold</b>）和斜体（<i>itatic</i>）需要翻译翻译内容并保留符号。
-   内联代码（<code>code</code>）和代码块不需要翻译。
-   链接（<a href='https://example.org'>link</a>）需要翻译其内容，但保留网址。
-   列表，表格，引用块保留格式，翻译内容
-   原文可能有多行，不要漏掉任何一行，并且注意一定不要重复输出原文！！！
-   输出应包含在“[content]...[/content]”中

## 示例

原文：

[content]
<ul><li><a href='https://wiki.example.org/feynmans_learning_method'>Feynman's learning method</a> is inspired by <b>Richard Feynman</b>, the Nobel Prize winner in physics. </li></ul>

<ol><li>With Feynman's skills, you can understand the knowledge points in depth in just <code>20 min</code>, and it is memorable and <i>hard to forget</i>. </li></ol>

<pre><code>
if (condVar > someVal) {console.log("xxx")}
</code></pre>
[/content]

译文：

[content]
<ul><li><a href='https://wiki.example.org/feynmans_learning_method'>费曼学习法</a>的灵感源于诺贝尔物理奖获得者<b>理查德·费曼</b>。</li></ul>

<ol><li>运用费曼技巧，你只需花上<code>20 min</code>就能深入理解知识点，而且记忆深刻，<i>难以遗忘</i>。</li></ol>

<pre><code>
if (condVar > someVal) {console.log("xxx")}
</code></pre>
[/content]

## 以下是需要翻译的文本

[content]
{text}
[/content]
'''
