#!/usr/bin/env python3
"""Zotero 雙向同步(Phase 7)

push:我們的論文 → Zotero(建立 journalArticle,依 DOI 去重,帶標籤與萃取摘要)
pull:Zotero → 我們(對有 PMID/DOI 但本地沒有的項目,建立深讀道文章;有 PMID 就抓 PMC 全文)

需要(env 或專案根目錄 .env):
  ZOTERO_API_KEY     https://www.zotero.org/settings/keys 產生(需 library 讀寫權)
  ZOTERO_USER_ID     同頁的 "Your userID"
  ZOTERO_COLLECTION  選填:只同步某個 collection 的 key(pull 用)

用法:
  python3 scripts/zotero_sync.py push        # 本地 → Zotero
  python3 scripts/zotero_sync.py pull        # Zotero → 本地
  python3 scripts/zotero_sync.py sync        # 先 pull 再 push
"""
import json
import os
import re
import subprocess
import sys
import urllib.request

try:
    import yaml
except ImportError:
    sys.exit("需要 PyYAML:pip install pyyaml")

ARTICLES_DIR = "src/content/articles"
API = "https://api.zotero.org"


def load_dotenv():
    if os.path.exists(".env"):
        for line in open(".env", encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def cfg():
    key = os.environ.get("ZOTERO_API_KEY")
    uid = os.environ.get("ZOTERO_USER_ID")
    if not key or not uid:
        sys.exit("✗ 需要 ZOTERO_API_KEY 與 ZOTERO_USER_ID(設 env 或寫進 .env)")
    return key, uid, os.environ.get("ZOTERO_COLLECTION", "").strip()


def zreq(method, path, key, body=None):
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Zotero-API-Key": key, "Content-Type": "application/json",
        "Zotero-API-Version": "3", "User-Agent": "nutrition-study-zotero",
    })
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode() or "null")


# ── 讀本地文章 ──
def split_fm(text):
    m = re.match(r"^---\n(.*?\n)---\n(.*)$", text, re.DOTALL)
    return (yaml.safe_load(m.group(1)), m.group(2)) if m else (None, text)


def local_articles():
    out = []
    for name in sorted(os.listdir(ARTICLES_DIR)):
        if not name.endswith(".md"):
            continue
        fm, _ = split_fm(open(os.path.join(ARTICLES_DIR, name), encoding="utf-8").read())
        if fm:
            out.append((name, fm))
    return out


def creators(authors):
    out = []
    for a in authors or []:
        parts = a.strip().split()
        if len(parts) >= 2:
            out.append({"creatorType": "author", "firstName": " ".join(parts[:-1]), "lastName": parts[-1]})
        elif parts:
            out.append({"creatorType": "author", "lastName": parts[0]})
    return out


# ── push ──
def existing_dois(key, uid):
    dois, start = set(), 0
    while True:
        items = zreq("GET", f"/users/{uid}/items/top?format=json&limit=100&start={start}", key)
        if not items:
            break
        for it in items:
            d = (it.get("data", {}).get("DOI") or "").lower().strip()
            if d:
                dois.add(d)
        if len(items) < 100:
            break
        start += 100
    return dois


def push():
    key, uid, coll = cfg()
    have = existing_dois(key, uid)
    new_items = []
    for name, fm in local_articles():
        doi = (fm.get("doi") or "").lower().strip()
        if not doi or doi in have:
            continue
        item = {
            "itemType": "journalArticle",
            "title": fm.get("title", ""),
            "creators": creators(fm.get("authors")),
            "publicationTitle": fm.get("journal", ""),
            "date": str(fm.get("pubDate", "")),
            "DOI": fm.get("doi", ""),
            "url": fm.get("link", ""),
            "tags": [{"tag": t} for t in (fm.get("tags") or [])],
            "extra": f"PMID: {fm.get('pmid','')}\nGRADE: {(fm.get('grade') or {}).get('certainty','')}",
        }
        if coll:
            item["collections"] = [coll]
        new_items.append(item)

    if not new_items:
        print("✔ Zotero 已是最新,沒有要推送的新項目。")
        return
    created = 0
    for i in range(0, len(new_items), 50):  # Zotero 一次最多 50 筆
        res = zreq("POST", f"/users/{uid}/items", key, new_items[i:i + 50])
        created += len(res.get("successful", {}))
        for f in res.get("failed", {}).values():
            print("  ✗ 失敗:", f.get("message"))
    print(f"✔ 已推送 {created} 篇到 Zotero。")


# ── pull ──
def pull():
    key, uid, coll = cfg()
    path = f"/users/{uid}/collections/{coll}/items/top" if coll else f"/users/{uid}/items/top"
    local_dois = {(fm.get("doi") or "").lower() for _, fm in local_articles()}
    start, imported = 0, 0
    while True:
        items = zreq("GET", f"{path}?format=json&limit=100&start={start}", key)
        if not items:
            break
        for it in items:
            d = it.get("data", {})
            doi = (d.get("DOI") or "").lower().strip()
            extra = d.get("extra", "") or ""
            pm = re.search(r"PMID:\s*(\d+)", extra)
            pmid = pm.group(1) if pm else ""
            if doi and doi in local_dois:
                continue
            if pmid:
                print(f"  ← 匯入 PMID {pmid}(抓 PMC 全文)")
                subprocess.run(["python3", "scripts/ingest.py", "pmc", pmid], check=False)
                imported += 1
            elif doi:
                print(f"  ← Zotero 有 DOI {doi} 但無 PMID/全文,略過(請手動上傳 PDF 後 ingest)")
        if len(items) < 100:
            break
        start += 100
    print(f"✔ 從 Zotero 匯入 {imported} 篇。")


def main():
    load_dotenv()
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "push":
        push()
    elif cmd == "pull":
        pull()
    elif cmd == "sync":
        pull()
        push()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
