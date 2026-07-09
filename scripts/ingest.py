#!/usr/bin/env python3
"""深讀道進料(Phase 1)

把「你上傳的 PDF」或「PMC 開放全文」轉成深讀道 markdown 文章,
放進 src/content/articles/,並用 Crossref 驗證 DOI(防幻覺)。

第二層萃取(PICO / RoB / 核心發現…)不在這裡做——這裡只負責
把「乾淨全文 + 驗證過的基本資訊」準備好,交給本機 Claude Code 的
extract-paper skill(Phase 2)。

用法:
  python scripts/ingest.py upload                 # 處理 pdfs/ 下所有 PDF
  python scripts/ingest.py upload path/to/x.pdf   # 處理單一 PDF
  python scripts/ingest.py pmc 42401201           # 用 PMID 抓 PMC 開放全文
  python scripts/ingest.py doi 10.1016/j....      # 只驗證/查詢一個 DOI

依賴:pip install 'markitdown[pdf]'
"""
import argparse
import json
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request

# macOS 內建 Python 常缺根憑證;優先用 certifi 的 CA bundle 建立 SSL context
try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _SSL_CTX = ssl.create_default_context()

ARTICLES_DIR = "src/content/articles"
PDF_DIR = "pdfs"
UA = {"User-Agent": "nutrition-study-ingest/1.0 (mailto:u9602041@gmail.com)"}

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", re.I)


# ────────────────────────────── HTTP 小工具 ──────────────────────────────
def _get(url, as_json=True, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as r:
        data = r.read().decode("utf-8", "replace")
    return json.loads(data) if as_json else data


# ────────────────────────────── Crossref 驗證 ──────────────────────────────
def crossref_lookup(doi):
    """回傳 {title, journal, year, authors} 或 None。用於防 AI/OCR 幻覺 DOI。"""
    doi = doi.strip().rstrip(".")
    try:
        msg = _get(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}")["message"]
    except Exception as e:
        print(f"  ⚠ Crossref 查無此 DOI 或連線失敗:{e}")
        return None
    title = (msg.get("title") or [""])[0]
    journal = (msg.get("container-title") or [""])[0]
    year = ""
    for k in ("published-print", "published-online", "published", "issued"):
        parts = (msg.get(k) or {}).get("date-parts")
        if parts and parts[0]:
            year = str(parts[0][0])
            break
    authors = []
    for a in msg.get("author", [])[:8]:
        nm = " ".join(x for x in [a.get("given"), a.get("family")] if x)
        if nm:
            authors.append(nm)
    return {"title": title, "journal": journal, "year": year, "authors": authors}


# ────────────────────────────── PMC 開放全文 ──────────────────────────────
def pmid_to_pmcid(pmid):
    url = ("https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
           f"?ids={pmid}&format=json&tool=nutrition-study&email=u9602041@gmail.com")
    try:
        recs = _get(url).get("records", [])
    except Exception as e:
        print(f"  ⚠ PMID→PMCID 轉換失敗:{e}")
        return None
    if recs and recs[0].get("pmcid"):
        return recs[0]["pmcid"]  # 形如 PMC1234567
    if recs and recs[0].get("status") == "error":
        print(f"  ⚠ 這篇沒有 PMC 紀錄(可能非開放取用):{recs[0].get('errmsg', '')}")
    return None


def fetch_pmc_fulltext(pmcid):
    """用 BioC API 取 PMC 開放全文。回傳 (全文字串, 權威DOI)。非 OA 會失敗回 (None, None)。"""
    url = ("https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/"
           f"BioC_json/{pmcid}/unicode")
    try:
        doc = _get(url)
    except Exception as e:
        print(f"  ⚠ 這篇不在 PMC 開放取用子集,無法取全文:{e}")
        return None, None
    # BioC 結構:[Collection] → Collection.documents → Document.passages
    collections = doc if isinstance(doc, list) else [doc]
    parts, doi = [], None
    for coll in collections:
        for d in coll.get("documents", [coll]):
            for p in d.get("passages", []):
                infons = p.get("infons") or {}
                if not doi and infons.get("article-id_doi"):
                    doi = infons["article-id_doi"]  # 權威 DOI,勝過全文正則
                txt = (p.get("text") or "").strip()
                if not txt:
                    continue
                section = infons.get("section_type", "")
                if section and section.upper() in ("TITLE", "ABSTRACT"):
                    parts.append(f"\n### {section.title()}\n{txt}")
                else:
                    parts.append(txt)
    return ("\n\n".join(parts) if parts else None), doi


# ────────────────────────────── markdown 產出 ──────────────────────────────
def _yaml_str(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', "'") + '"'


def build_frontmatter(meta):
    tags = "[" + ", ".join(_yaml_str(t) for t in meta.get("tags", [])) + "]"
    authors = "[" + ", ".join(_yaml_str(a) for a in meta.get("authors", [])) + "]"
    return f"""---
title: {_yaml_str(meta.get('title',''))}
journal: {_yaml_str(meta.get('journal',''))}
category: {_yaml_str(meta.get('category','未分類'))}
pubDate: {_yaml_str(meta.get('pubDate',''))}
link: {_yaml_str(meta.get('link',''))}
doi: {_yaml_str(meta.get('doi',''))}
pmid: {_yaml_str(meta.get('pmid',''))}
tags: {tags}
authors: {authors}
depth: "reading"
fulltext_source: {_yaml_str(meta.get('fulltext_source','upload'))}
study_design: ""
sample_size: ""
inclusion: ""
exclusion: ""
instruments: []
statistics: []
limitations_stated: ""
funding: ""
coi: ""
pico:
  ai_draft: ""
  confirmed: ""
rob:
  tool: ""
  ai_draft: ""
  confirmed: ""
key_findings:
  ai_draft: ""
  confirmed: ""
gap:
  ai_draft: ""
  confirmed: ""
grade:
  certainty: ""
  ai_draft: ""
  confirmed: ""
spin:
  ai_draft: ""
  confirmed: ""
ref_check: ""
related: []
my_notes: ""
---
"""


def write_article(meta, fulltext, slug):
    os.makedirs(ARTICLES_DIR, exist_ok=True)
    path = os.path.join(ARTICLES_DIR, f"{slug}.md")
    if os.path.exists(path):
        print(f"  ⏭ 已存在,略過(避免覆蓋你已編輯的內容):{path}")
        print(f"     若要重抓請先手動刪除該檔。")
        return None
    body = (
        "\n## 核心發現\n\n<!-- 待 Phase 2 extract-paper 產草稿,或你自行填寫 -->\n"
        "\n## 證據等級 / 風險偏誤\n\n"
        "\n## 延伸想法 / 研究缺口\n\n"
        "\n## 與其他文獻的關聯\n\n"
        "\n## 個人評語\n\n"
        "\n## 原文全文 (Full text)\n\n"
        "> 以下為 markitdown/PMC 萃取的原文,供 Phase 2 AI 萃取閱讀。\n\n"
        + (fulltext or "(無全文內容)") + "\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(build_frontmatter(meta) + body)
    print(f"  ✓ 已建立深讀道文章:{path}")
    return path


def _slugify(text, maxlen=50):
    text = re.sub(r'[\\/*?:"<>|]', "", text).strip()
    text = re.sub(r"\s+", " ", text)
    return text[:maxlen].strip() or "untitled"


# ────────────────────────────── 指令:upload ──────────────────────────────
def cmd_upload(paths):
    from markitdown import MarkItDown
    md = MarkItDown()

    if not paths:
        if not os.path.isdir(PDF_DIR):
            print(f"找不到 {PDF_DIR}/,請先建立並放入 PDF。")
            return
        paths = [os.path.join(PDF_DIR, f) for f in sorted(os.listdir(PDF_DIR))
                 if f.lower().endswith(".pdf")]
    if not paths:
        print(f"{PDF_DIR}/ 下沒有 PDF。把論文 PDF 丟進去再跑一次。")
        return

    for pdf in paths:
        print(f"處理:{pdf}")
        try:
            fulltext = md.convert(pdf).text_content
        except Exception as e:
            print(f"  ✗ markitdown 轉換失敗:{e}")
            continue
        if not fulltext or len(fulltext) < 100:
            print("  ⚠ 轉出內容過短,可能是掃描影像 PDF(需 OCR),已略過。")
            continue

        # 從全文正則找 DOI → Crossref 取得權威基本資訊(防幻覺)
        meta = {"fulltext_source": "upload", "tags": []}
        m = DOI_RE.search(fulltext)
        base = os.path.splitext(os.path.basename(pdf))[0]
        # 若檔名就是 PMID(純數字),記錄之
        if base.isdigit():
            meta["pmid"] = base
        if m:
            doi = m.group(0)
            meta["doi"] = doi
            cr = crossref_lookup(doi)
            if cr:
                meta.update(title=cr["title"], journal=cr["journal"],
                            pubDate=cr["year"], authors=cr["authors"])
                print(f"  ✓ Crossref 驗證通過:{cr['title'][:60]}… ({cr['journal']}, {cr['year']})")
        if not meta.get("title"):
            # Crossref 沒查到 → 用檔名當暫定標題,基本資訊留白待你補
            meta["title"] = f"[待補基本資訊] {base}"
            print("  ⚠ 沒抓到可驗證的 DOI,基本資訊留白,請在 frontmatter 補齊。")

        slug = base if base.isdigit() else _slugify(base)
        write_article(meta, fulltext, slug)


# ────────────────────────────── 指令:pmc ──────────────────────────────
def cmd_pmc(pmid):
    pmid = pmid.strip()
    print(f"PMID {pmid} → 查 PMC 開放全文…")
    pmcid = pmid_to_pmcid(pmid)
    if not pmcid:
        print("  ✗ 沒有可用的 PMC 開放全文。改用 PDF 上傳這篇。")
        return
    print(f"  PMCID = {pmcid}")
    fulltext, doi = fetch_pmc_fulltext(pmcid)
    if not fulltext:
        print("  ✗ 取全文失敗。")
        return

    meta = {"pmid": pmid, "fulltext_source": "pmc", "tags": [],
            "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"}
    # 優先用 BioC 的權威 DOI;沒有再退回全文正則
    if not doi:
        m = DOI_RE.search(fulltext)
        doi = m.group(0) if m else None
    if doi:
        cr = crossref_lookup(doi)
        if cr:
            meta.update(doi=doi, title=cr["title"], journal=cr["journal"],
                        pubDate=cr["year"], authors=cr["authors"])
            print(f"  ✓ Crossref:{cr['title'][:60]}…")
        else:
            meta["doi"] = doi
    if not meta.get("title"):
        meta["title"] = f"[待補基本資訊] PMID {pmid}"

    write_article(meta, fulltext, pmid)


# ────────────────────────────── 指令:doi ──────────────────────────────
def cmd_doi(doi):
    cr = crossref_lookup(doi)
    if cr:
        print(json.dumps(cr, ensure_ascii=False, indent=2))
    else:
        print("查無資料。")


def main():
    ap = argparse.ArgumentParser(description="深讀道進料")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_up = sub.add_parser("upload", help="處理 PDF(預設整個 pdfs/)")
    p_up.add_argument("paths", nargs="*", help="指定 PDF 路徑,省略則掃 pdfs/")
    p_pmc = sub.add_parser("pmc", help="用 PMID 抓 PMC 開放全文")
    p_pmc.add_argument("pmid")
    p_doi = sub.add_parser("doi", help="只驗證/查詢一個 DOI")
    p_doi.add_argument("doi")
    args = ap.parse_args()

    if args.cmd == "upload":
        cmd_upload(args.paths)
    elif args.cmd == "pmc":
        cmd_pmc(args.pmid)
    elif args.cmd == "doi":
        cmd_doi(args.doi)


if __name__ == "__main__":
    main()
