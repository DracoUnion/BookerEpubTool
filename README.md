# BookerEpubTool

iBooker/ApacheCN 知识库抓取工具

## 安装

通过pip（推荐）：

```
pip install BookerEpubTool
```

从源码安装：

```
pip install git+https://github.com/apachecn/BookerEpubTool
```

安装后可使用两个入口命令：

```
BookerEpubTool <命令> [参数]
epub-tool <命令> [参数]
```

也可以不安装、直接用模块方式运行：

```
python -m BookerEpubTool <命令> [参数]
```

## 使用说明

```
usage: BookerEpubTool [-h] [-v] [公共参数] {comp,toc,ext-chs,ext-htmls,ext-pics,sel-nocd,fmt-para,mkds,add-title,trans} ...
```

支持以下子命令：

| 命令 | 作用 |
|---|---|
| `comp` | 压缩 EPUB 内的图片，减小体积 |
| `toc` | 查看 EPUB 目录 |
| `ext-chs` | 导出 EPUB 章节（合并为 HTML） |
| `ext-htmls` | 导出 EPUB 中的 HTML 文件 |
| `ext-pics` | 导出 EPUB 中的图片 |
| `sel-nocd` | 筛选不含代码的 EPUB |
| `fmt-para` | 格式化段落（合并过短的段） |
| `mkds` | 将 EPUB 段落导出为 YAML 数据集 |
| `add-title` | 为章节补写标题 |
| `trans` | 翻译 EPUB（调用 GPT 模型） |

每个子命令的完整参数可通过 `-h/--help` 查看。`trans` 需要 OpenAI 兼容 API，公共参数（`-m` 模型、`-k` Key、`-H` 地址等）置于子命令之前，详见下文 `trans` 小节。

### comp：压缩 EPUB 图片

优化 EPUB 内所有图片并**原位覆盖写入原文件**（会直接改写原文件，请先备份）。

```
BookerEpubTool comp example.epub
BookerEpubTool comp -m quant -c 16 example.epub
```

| 参数 | 说明 | 默认值 |
|---|---|---|
| `file` | EPUB 文件；`.mobi`/`.azw3` 会先用 Calibre 的 `ebook-convert` 转为 EPUB | 必填 |
| `-m, --mode` | 压缩模式：`quant`（pngquant 量化）/ `grid` / `trunc`（截断至 N 色）/ `thres` | `quant` |
| `-c, --color` | `quant` 与 `trunc` 模式的颜色数 | `8` |

### toc：查看 EPUB 目录

打印目录树，级别用 `>` 缩进，格式为 `序号-原序号：src`。可用于配合 `ext-chs` 观察标题正则与层级。

```
BookerEpubTool toc example.epub
BookerEpubTool toc -l 2 example.epub
BookerEpubTool toc -r 第.章 example.epub
```

| 参数 | 说明 | 默认值 |
|---|---|---|
| `fname` | EPUB 文件 | 必填 |
| `-l, --hlevel` | 保留目录级别 ≤ 该值的条目；`0` 表示全部 | `0` |
| `-r, --regex` | 正则，仅保留标题匹配的条目 | 无 |

### ext-chs：导出 EPUB 章节

以目录条目所在文件为界拆分章节，合并后按编号输出独立的 HTML 文件。

```
BookerEpubTool ext-chs example.epub
BookerEpubTool ext-chs -d out -s 1 -e 5 example.epub
BookerEpubTool ext-chs -a example.epub
```

| 参数 | 说明 | 默认值 |
|---|---|---|
| `fname` | EPUB 文件 | 必填 |
| `-d, --dir` | 输出目录 | `.` |
| `-s, --start` | 起始章节下标（从 0 计）；`-1` 表示全部 | `-1` |
| `-e, --end` | 结束章节下标；`-1` 表示全部 | `-1` |
| `-l, --hlevel` | 按该层级截取目录，用于判定章节边界 | `0` |
| `-r, --regex` | 正则过滤目录，用于判定章节边界 | 无 |
| `-p, --prefix` | 输出文件前缀 | 空 |
| `-a, --all-in-one` | 将所有章节合并输出为一个 `{书名}.html` | 关 |

### ext-htmls：导出版本内全部 HTML

把 EPUB 里所有 `.html`/`.htm`/`.xhtml` 条目导出到目录，统一以 `.html` 结尾。

```
BookerEpubTool ext-htmls example.epub
BookerEpubTool ext-htmls -o out -p src- example.epub
```

| 参数 | 说明 | 默认值 |
|---|---|---|
| `fname` | EPUB 文件 | 必填 |
| `-o, --output-dir` | 输出目录 | `.` |
| `-p, --prefix` | 输出文件前缀 | 空 |

### ext-pics：导出 EPUB 内全部图片

```
BookerEpubTool ext-pics example.epub
BookerEpubTool ext-pics -o pics example.epub
```

| 参数 | 说明 | 默认值 |
|---|---|---|
| `fname` | EPUB 文件 | 必填 |
| `-o, --output-dir` | 输出目录 | `.` |
| `-p, --prefix` | 输出文件前缀 | 空 |

### sel-nocd：筛选不含代码的 EPUB

若 EPUB 中没有任何 HTML 含 `<code>`（即无代码示例），则把文件移动到输出目录。

```
BookerEpubTool sel-nocd example.epub
```

| 参数 | 说明 | 默认值 |
|---|---|---|
| `fname` | EPUB 文件 | 必填 |
| `-o, --output-dir` | 命中后移动到的目录 | `.` |

### fmt-para：格式化段落

把长度在 `[low, high]` 区间、且正文不以句末标点结尾的短段落合并到下一段，**原位覆盖写入原文件**（请先备份）。常用于清理排版不端的 EPUB。

```
BookerEpubTool fmt-para example.epub
BookerEpubTool fmt-para -l 20 -u 50 example.epub
```

| 参数 | 说明 | 默认值 |
|---|---|---|
| `fname` | EPUB 文件 | 必填 |
| `-l, --low` | 触发合并的段落长度下界 | `30` |
| `-u, --high` | 触发合并的段落长度上界 | `35` |

### mkds：导出 YAML 数据集

逐章取标题和段落，输出 `{书名}.yaml`。用于构造细粒度文本数据集（如问答、润色任务）。

```
BookerEpubTool mkds example.epub
BookerEpubTool mkds -w example.epub
```

| 参数 | 说明 | 默认值 |
|---|---|---|
| `fname` | EPUB 文件 | 必填 |
| `-t, --title` | 标题的 CSS 选择器 | `h1` |
| `-p, --paras` | 段落的 CSS 选择器 | `p` |
| `-w, --whole` | 把 `<body>` 整体按行拆分为段落 | 关 |

### add-title：为章节补写标题

对每个目录条目，若章节正文首元素不是与目录标题一致的 `h1/h2/h3`，则在其头部插入 `<h1>`，**原位覆盖写入原文件**（请先备份）。

```
BookerEpubTool add-title example.epub
```

| 参数 | 说明 | 默认值 |
|---|---|---|
| `fname` | EPUB 文件 | 必填 |

### trans：翻译 EPUB

调用 GPT 兼容模型把英文 EPUB 翻译为中文，按章节输出 Markdown。翻译过程分 8 步：初始化元数据 → 转换 HTML/MD → 导出图片 → 排版+翻译 → 修正目录 → 分章节 → 生成 README/SUMMARY。中间产物缓存到 `{书名}/asset/` 目录，已完成的步骤断点续跑不会重复消耗 API。

```
BookerEpubTool -m gpt-4o trans example.epub
BookerEpubTool -m gpt-4o -H http://localhost:8000/v1 -k sk-xxx trans example.epub
BookerEpubTool -m deepseek-chat trans -D --clean --split example.epub
BookerEpubTool -m o3-mini trans -D --clean --split example.epub
```

| 参数 | 说明 | 默认值 |
|---|---|---|
| `fname` | EPUB 文件或目录；目录会递归选取其中全部 `.epub` | 必填 |
| `-ft, --file-threads` | 文件线程数 | `1` |
| `-pt, --page-threads` | 页面（分块）线程数 | `8` |
| `-l, --limit` | 分块大小上限 | `8000` |
| `-m, --fmt-mode` | 转换格式模式：`none` / `oreilly` / `packt` / `apress` | `none` |
| `-D, --debug`（全局） | 调试模式（输出详细日志） | 关 |
| `--split` | 是否用 GPT 识别章节边界并拆分为章 | 关 |
| `--clean` | 是否用 GPT 清理版权页/目录等前置内容 | 关 |
| `-sl, --split-limit` | 划分章节的分块大小上限 | `3000` |
| `-so, --split-overlap` | 划分章节的分块重叠大小 | `50` |

注意 `-m` 的双重语义：位于 `trans` 之前时是**模型名**（主命令参数），位于 `trans` 之后时是 `--fmt-mode`（子命令参数）。其余公共参数（`-k` Key、`-H` API 地址、`-tm` 温度、`-r` 重试等）同样须置于 `trans` 之前。

示例：`BookerEpubTool -m qwen3-max trans -m oreilly example.epub` 表示用 qwen3-max 模型翻译、按 O'Reilly 格式预处理。

## 协议

本项目基于 SATA 协议发布。

您有义务为此开源项目点赞，并考虑额外给予作者适当的奖励。

## 赞助我们

![](https://home.apachecn.org/img/about/donate.jpg)

## 另见

+   [ApacheCN 学习资源](https://docs.apachecn.org/)
+   [计算机电子书](http://it-ebooks.flygon.net)
+   [布客新知](http://flygon.net/ixinzhi/)