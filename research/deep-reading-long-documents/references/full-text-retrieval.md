# 抓取长文档全文并实读

用于：用户要求「读一下这本书/这份报告/这篇论文」。目标是真读，不是复述训练记忆。

## 1. 下载：archive.org 两种路径

```bash
# 路径 A：全文纯文本（对部分 item 返回 404）
curl -sL --max-time 180 -o doc.txt \
 "https://archive.org/stream/<item>/<FILE>%20djvu.txt"

# 路径 B：直接下 PDF（必须带正确的分片主机名）
curl -sL --max-time 240 -A "Mozilla/5.0" -o tmp.pdf \
 "https://ia801400.us.archive.org/23/items/<item>/<FILE>.pdf"
file tmp.pdf   # 确认是 PDF，不是错误页
```

⚠️ `web_extract` 遇 archive.org 的 djvu 网页版常返回空 / 被拒（"Upstream forbidden"）。别在它身上耗时间，直接 curl + 本地解析。

⚠️ PDF 直链必须带正确的 `ia######.us.archive.org` 分片主机名；猜主机名会 404。分片号从 archive.org item 页或搜索结果 URL 里读。

## 2. 转纯文本 + 核对规模

```bash
pdftotext -layout tmp.pdf doc.txt
# 没有 pdftotext 时：
# python3 -c "from pypdf import PdfReader; r=PdfReader('tmp.pdf'); \
#   open('doc.txt','w').write('\n\n'.join((p.extract_text() or '') for p in r.pages))"

wc -l -w -c doc.txt
grep -n -E "^ *(PART|Chapter|第[一二三四五六七八九十]+[章节篇])" doc.txt | head -60
```

`wc` 结果就是后面要报给用户的可核对数字。**没跑过的数字不许写。**

## 3. 分页读

```
read_file(path=doc.txt, offset=<递进>, limit=1200)
```

每次 ~1200 行，按 offset 递进读完，不跳读。8000 行书 ≈ 7 次调用；调用数本身就是「真读」的证据。

临时文件放 scratch 目录（`~/.hermes/cache/scratch`），别写系统 temp。

## 4. 已知坑

- `/stream/<item>/<FILE>_djvu.txt` 对某些 item 是 404，换 PDF 路径
- 中译本常把多个原始小节合并，目录对不上原版属正常，但**必须说清是哪个版本**
- 用户要「体会」不要「摘要」：至少给一条自己的批判
- 结构类字段（章节数 / 篇章划分）最容易凭印象报错 —— 这是用户验证你的第一入口