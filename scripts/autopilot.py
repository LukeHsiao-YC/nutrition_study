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
    # transport='rest' 繞過 gRPC(避免背景輪詢/fork 情境下卡住)
    genai.configure(api_key=key, transport="rest")

    # 動態挑選可用的 flash 模型(避開已淘汰的 1.5、以及 image/tts/preview 等特殊版)
    preferred = ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-flash-lite",
                 "gemini-2.0-flash-lite")
    try:
        avail = {
            m.name.replace("models/", "")
            for m in genai.list_models()
            if "generateContent" in m.supported_generation_methods
        }
    except Exception:
        avail = set()
    for name in preferred:
        if name in avail:
            return genai.GenerativeModel(name)
    # 退而求其次:任何一般 flash(排除 image/tts/preview/exp)
    for name in sorted(avail):
        if "flash" in name and not any(x in name for x in ("image", "tts", "preview", "exp")):
            return genai.GenerativeModel(name)
    sys.exit("✗ 找不到可用的 Gemini flash 模型,請檢查金鑰權限。")


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


def extract_with_gemini_prompt(model, prompt, fulltext):
    resp = model.generate_content(prompt.replace("{fulltext}", fulltext))
    m = re.search(r"\{.*\}", resp.text, re.DOTALL)
    if not m:
        raise ValueError("Gemini 未回傳 JSON")
    return json.loads(m.group(0))


def extract_with_gemini(model, fulltext):
    return extract_with_gemini_prompt(model, PROMPT, fulltext)


def run(cmd):
    print("  $", " ".join(cmd))
    return subprocess.run(cmd, check=False)


# ── Phase 7:批判性評讀(Gemini 評級 → 確定性程式計算)──
REVIEW_PROMPT = """你是實證醫學評讀助理。根據以下論文全文,輸出「只有 JSON」:
{
 "is_protocol": true/false,            // 研究計畫/無結果時 true
 "starting_level": "high"或"low",       // RCT=high;觀察性=low
 "grade_domains": [                     // 五個 GRADE 降級面向
   {"name":"risk_of_bias","rating":"not_serious|serious|very_serious"},
   {"name":"inconsistency","rating":"..."},
   {"name":"indirectness","rating":"..."},
   {"name":"imprecision","rating":"..."},
   {"name":"publication_bias","rating":"..."}
 ],
 "upgrades": [],                        // 僅觀察性且無降級時,如 {"name":"large_effect","rating":"serious"}
 "rob_tool": "依設計:Cochrane-RoB2/Newcastle-Ottawa/ROBINS-I/AMSTAR-2/QUADAS-2/PROBAST/AGREE-II/SANRA/JBI;protocol填N/A",
 "claims": [                            // 論文 1-3 個主要結論
   {"claim":"...","claim_type":"hard_endpoint|causal|benefit|association|descriptive",
    "premises":[{"type":"direct_rct|association|surrogate_outcome|single_study|subgroup|secondary_outcome|mechanistic|expert_opinion"}]}
 ],
 "notes": "GRADE 降級/RoB 的一句話理由(繁中)"
}
只依全文判斷,不確定就保守。全文:
---
{fulltext}
"""


def _capture_json(script, payload):
    """呼叫 grade_judge/argdown_lint,回傳其 stdout 的 JSON(退出碼非0不視為錯誤)。"""
    p = subprocess.run(["python3", script, "-"], input=json.dumps(payload),
                       capture_output=True, text=True)
    try:
        return json.loads(p.stdout)
    except Exception:
        return None


def review_article(model, path):
    """對一篇已有全文的文章跑評讀:Gemini 評級 → grade_judge + argdown_lint → 寫回。"""
    _, body = split_frontmatter(open(path, encoding="utf-8").read())
    try:
        r = extract_with_gemini_prompt(model, REVIEW_PROMPT, get_fulltext(body))
    except Exception as e:
        print(f"    ✗ 評讀失敗,略過:{e}")
        return

    out = {"rob_tool": r.get("rob_tool", "")}
    if r.get("is_protocol"):
        out["grade_certainty"] = ""
        out["grade"] = "GRADE 不適用:研究計畫/無結果。" + (r.get("notes") or "")
    else:
        gj = _capture_json("scripts/grade_judge.py", {
            "starting_level": r.get("starting_level", "high"),
            "domains": r.get("grade_domains", []),
            "upgrades": r.get("upgrades", []),
        })
        if gj:
            out["grade_certainty"] = gj.get("certainty", "")
            downs = gj.get("downgrades", 0)
            out["grade"] = f"GRADE:{gj.get('starting_level')} 起始,降 {downs} 級 → {gj.get('certainty')}。{r.get('notes','')}"

    al = _capture_json("scripts/argdown_lint.py", {"claims": r.get("claims", [])})
    if al is not None:
        gaps = [g for c in al.get("claims", []) for g in c.get("gaps", [])]
        out["spin"] = ("發現過度推論:" + "；".join(gaps)) if gaps else "argdown_lint 未發現明顯過度推論。"

    with open(TMP_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    run(["python3", "scripts/apply_extraction.py", path, TMP_JSON])


def process_all(do_ingest=True, do_review=True):
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
        if do_review:
            print("    ⚖ 批判性評讀(GRADE + spin)…")
            review_article(model, path)
        done += 1
        time.sleep(2)  # 對 API 友善
    print(f"✔ 完成萃取{'＋評讀' if do_review else ''} {done}/{len(pending)} 篇。")
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


def watch(push, do_review=True):
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
            if process_all(do_ingest=True, do_review=do_review) and push:
                git_push()
            seen = set(glob.glob(os.path.join(PDF_DIR, "*.pdf")))


def main():
    load_dotenv()
    ap = argparse.ArgumentParser(description="全自動深讀道(Gemini)")
    ap.add_argument("--push", action="store_true", help="完成後 git commit + push")
    ap.add_argument("--watch", action="store_true", help="監看 pdfs/ 自動處理")
    ap.add_argument("--no-ingest", action="store_true", help="跳過進料,只萃取")
    ap.add_argument("--no-review", action="store_true", help="只萃取內容,不跑 GRADE/spin 評讀")
    args = ap.parse_args()

    if args.watch:
        watch(args.push, do_review=not args.no_review)
    else:
        n = process_all(do_ingest=not args.no_ingest, do_review=not args.no_review)
        if n and args.push:
            git_push()


if __name__ == "__main__":
    main()
