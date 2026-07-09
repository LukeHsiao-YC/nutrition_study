#!/usr/bin/env python3
"""全自動深讀道:丟 PDF → 自動進料 + 用 Gemini 萃取 + 寫回(可選 commit/push)

這是「等級二」自動化:不需要在 Claude Code 出場,靠 Gemini API 做萃取。
品質通常略低於 Claude Code 的 extract-paper skill,適合「丟檔就自動、量大」時使用。

用法:
  python3 scripts/autopilot.py            # 進料 + 萃取所有待處理文章
  python3 scripts/autopilot.py --push     # 完成後自動 git commit + push
  python3 scripts/autopilot.py --watch     # 監看 pdfs/,一有新 PDF 就自動跑
  python3 scripts/autopilot.py --no-ingest # 跳過進料,只萃取已存在的待處理文章

需要:
  - pip install -r requirements.txt(google-generativeai, pyyaml…)
  - 環境變數 GEMINI_API_KEY,或在專案根目錄放 .env:  GEMINI_API_KEY=xxxx
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time

try:
    import yaml
except ImportError:
    sys.exit("需要 PyYAML:pip install pyyaml")

ARTICLES_DIR = "src/content/articles"
PDF_DIR = "pdfs"
TMP_JSON = "/tmp/nutrition_autopilot_extract.json"


# ── .env 極簡載入(免額外套件)────────────────────────────
def load_dotenv():
    if os.path.exists(".env"):
        for line in open(".env", encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def get_model():
    import google.generativeai as genai
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit("✗ 找不到 GEMINI_API_KEY。請 export GEMINI_API_KEY=... 或寫進專案根目錄 .env")
    genai.configure(api_key=key)
    for name in ("gemini-1.5-flash", "gemini-1.5-pro"):
        try:
            return genai.GenerativeModel(name)
        except Exception:
            continue
    return genai.GenerativeModel("gemini-1.5-flash")


# ── 找出待萃取文章:depth=reading 且第二層 pico.ai_draft 還空著 ──
def split_frontmatter(text):
    m = re.match(r"^---\n(.*?\n)---\n(.*)$", text, re.DOTALL)
    if not m:
        return None, text
    return yaml.safe_load(m.group(1)), m.group(2)


def needs_extraction(fm):
    if not fm or fm.get("depth") != "reading":
        return False
    pico = fm.get("pico") or {}
    return not (pico.get("ai_draft") or "").strip()


def get_fulltext(body):
    m = re.search(r"## 原文全文.*?\n(.*)$", body, re.DOTALL)
    txt = m.group(1) if m else body
    return txt[:120000]  # 保守截斷,避免超長


PROMPT = """你是嚴謹的實證醫學研究助理。以下是一篇醫學/營養論文的全文。
請「只根據全文」萃取,找不到的欄位一律留空字串或空陣列,絕不憑常識或記憶補;
數字(樣本數、p 值等)須與原文一致,不確定就留空。若這是研究計畫(protocol)或
尚無結果,核心發現要誠實寫「尚無結果」,不得捏造。

請「只輸出 JSON」(不要 markdown 標記、不要說明),鍵與型別如下,值用繁體中文:
{
 "study_design": "字串", "sample_size": "字串",
 "inclusion": "字串", "exclusion": "字串",
 "instruments": ["字串"], "statistics": ["字串"],
 "limitations_stated": "作者自陳限制", "funding": "資助來源", "coi": "利益衝突",
 "tags": ["3-5個繁中主題標籤"],
 "pico": "P:.. I:.. C:.. O:..",
 "key_findings": "2-4句核心發現,帶關鍵數字;protocol 則寫尚無結果",
 "gap": "研究缺口/未來方向",
 "rob_tool": "依設計選:RCT→Cochrane-RoB2;世代/病例對照→Newcastle-Ottawa;系統回顧→AMSTAR-2;protocol→N/A",
 "rob": "2-4句風險偏誤簡評 + 整體評級"
}

全文如下:
---
{fulltext}
"""


def extract_with_gemini(model, fulltext):
    resp = model.generate_content(PROMPT.replace("{fulltext}", fulltext))
    raw = resp.text
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        raise ValueError("Gemini 未回傳 JSON")
    return json.loads(m.group(0))


def run(cmd):
    print("  $", " ".join(cmd))
    return subprocess.run(cmd, check=False)


def process_all(do_ingest=True):
    if do_ingest:
        print("▶ 進料(ingest upload)…")
        run(["python3", "scripts/ingest.py", "upload"])

    pending = []
    for path in sorted(glob.glob(os.path.join(ARTICLES_DIR, "*.md"))):
        fm, _ = split_frontmatter(open(path, encoding="utf-8").read())
        if needs_extraction(fm):
            pending.append(path)

    if not pending:
        print("✔ 沒有待萃取的文章。")
        return 0

    print(f"▶ 待萃取 {len(pending)} 篇,開始用 Gemini 萃取…")
    model = get_model()
    done = 0
    for path in pending:
        print(f"  ◦ {os.path.basename(path)}")
        _, body = split_frontmatter(open(path, encoding="utf-8").read())
        try:
            data = extract_with_gemini(model, get_fulltext(body))
        except Exception as e:
            print(f"    ✗ 萃取失敗,略過:{e}")
            continue
        with open(TMP_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        run(["python3", "scripts/apply_extraction.py", path, TMP_JSON])
        done += 1
        time.sleep(2)  # 對 API 友善
    print(f"✔ 完成萃取 {done}/{len(pending)} 篇。")
    return done


def git_push():
    print("▶ build 驗證 + commit + push…")
    if run(["npm", "run", "build"]).returncode != 0:
        print("✗ build 失敗,略過 commit。請先修正。")
        return
    run(["git", "add", "-A"])
    run(["git", "commit", "-m", "autopilot: 自動進料+萃取深讀道論文"])
    run(["git", "pull", "--rebase", "origin", "main"])
    run(["git", "push", "origin", "main"])


def watch(push):
    seen = set(glob.glob(os.path.join(PDF_DIR, "*.pdf")))
    print(f"👀 監看 {PDF_DIR}/ …(Ctrl+C 停止)。目前已有 {len(seen)} 個 PDF。")
    print("   丟新 PDF 進去就會自動處理。")
    while True:
        time.sleep(8)
        now = set(glob.glob(os.path.join(PDF_DIR, "*.pdf")))
        new = now - seen
        if new:
            print(f"\n🔔 偵測到新 PDF:{[os.path.basename(p) for p in new]}")
            time.sleep(2)  # 等檔案寫完
            if process_all(do_ingest=True) and push:
                git_push()
            seen = set(glob.glob(os.path.join(PDF_DIR, "*.pdf")))


def main():
    load_dotenv()
    ap = argparse.ArgumentParser(description="全自動深讀道(Gemini)")
    ap.add_argument("--push", action="store_true", help="完成後 git commit + push")
    ap.add_argument("--watch", action="store_true", help="監看 pdfs/ 自動處理")
    ap.add_argument("--no-ingest", action="store_true", help="跳過進料,只萃取")
    args = ap.parse_args()

    if args.watch:
        watch(args.push)
    else:
        n = process_all(do_ingest=not args.no_ingest)
        if n and args.push:
            git_push()


if __name__ == "__main__":
    main()
