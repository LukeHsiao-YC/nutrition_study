#!/usr/bin/env python3
"""把深讀道論文轉成 Marp 投影片 markdown(離線、免外部服務的快速版)

這是 paper-to-slides 的「離線後備」路徑;若要 AI 生成精美投影片,
用 .claude/skills/paper-to-slides(串 notebooklm-research skill)。

輸出優先採用你確認過的 confirmed,沒有才用 ai_draft。
用法:
  python scripts/paper_to_marp.py src/content/articles/38572369.md
  → 產生 slides/38572369.md,可用 Marp for VS Code / marp-cli 轉 PDF/PPTX
"""
import os
import re
import sys

try:
    import yaml
except ImportError:
    sys.exit("需要 PyYAML:pip install pyyaml")


def load(md_path):
    text = open(md_path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?\n)---\n", text, re.DOTALL)
    if not m:
        sys.exit("✗ 找不到 frontmatter。")
    return yaml.safe_load(m.group(1))


def pick(pair):
    if not isinstance(pair, dict):
        return ""
    return (pair.get("confirmed") or pair.get("ai_draft") or "").strip()


def slide(title, body):
    body = (body or "").strip()
    return f"## {title}\n\n{body if body else '_（尚無內容）_'}\n"


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    src = sys.argv[1]
    d = load(src)

    authors = "、".join(d.get("authors") or [])
    year = (re.search(r"\d{4}", str(d.get("pubDate", ""))) or [None])
    year = year.group(0) if hasattr(year, "group") else (d.get("pubDate") or "")

    methods = []
    for label, key in [("設計", "study_design"), ("樣本數", "sample_size"),
                       ("收案", "inclusion"), ("排除", "exclusion")]:
        if d.get(key):
            methods.append(f"- **{label}**:{d[key]}")
    for label, key in [("量表/工具", "instruments"), ("統計方法", "statistics")]:
        if d.get(key):
            methods.append(f"- **{label}**:{'、'.join(d[key])}")
    methods_body = "\n".join(methods)

    rob_tool = (d.get("rob") or {}).get("tool", "")
    rob_body = (f"**工具:{rob_tool}**\n\n" if rob_tool else "") + pick(d.get("rob"))

    cite = []
    if authors:
        cite.append(authors)
    if d.get("journal"):
        cite.append(f"*{d['journal']}*")
    if year:
        cite.append(str(year))
    if d.get("doi"):
        cite.append(f"DOI: {d['doi']}")
    cite_body = " · ".join(cite)

    deck = f"""---
marp: true
theme: default
paginate: true
---

# {d.get('title','(無標題)')}

{authors}
{('*' + d['journal'] + '*') if d.get('journal') else ''} {year}

---

{slide('研究問題與設計（PICO）', pick(d.get('pico')))}
---

{slide('方法', methods_body)}
{('作者自陳限制:' + d['limitations_stated']) if d.get('limitations_stated') else ''}

---

{slide('核心發現', pick(d.get('key_findings')))}
---

{slide('證據等級 / 風險偏誤', rob_body)}
---

{slide('研究缺口 / 延伸想法', pick(d.get('gap')))}
---

{slide('個人評語', d.get('my_notes',''))}
---

## 引用

{cite_body}
"""

    os.makedirs("slides", exist_ok=True)
    base = os.path.splitext(os.path.basename(src))[0]
    out = os.path.join("slides", f"{base}.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(deck)
    print(f"✓ 已產生 Marp 投影片:{out}")
    print("  轉檔:npx @marp-team/marp-cli " + out + " --pdf   (或 --pptx)")


if __name__ == "__main__":
    main()
