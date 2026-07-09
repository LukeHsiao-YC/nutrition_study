#!/usr/bin/env python3
"""把萃取結果(JSON)安全寫回深讀道文章的 frontmatter(Phase 2 helper)

設計原則:
- 只更新「第一層欄位」與「第二層的 ai_draft / rob.tool」。
- 絕不覆蓋你已填的 confirmed、related、my_notes、內文(body)。
- 找不到的欄位保持原樣;逐行定點替換,不重新序列化整份 YAML(diff 乾淨)。

用法:
  python scripts/apply_extraction.py <article.md> <extraction.json>
  python scripts/apply_extraction.py <article.md> -        # JSON 從 stdin 讀

extraction.json 可含的鍵(全部選填):
  study_design, sample_size, inclusion, exclusion,
  instruments(陣列), statistics(陣列), tags(陣列),
  limitations_stated, funding, coi,
  pico, key_findings, gap                # → 各自的 ai_draft
  rob_tool, rob                          # → rob.tool / rob.ai_draft
"""
import json
import re
import sys

# 第一層純量欄位(頂層 key: "value")
SCALAR_KEYS = ["study_design", "sample_size", "inclusion", "exclusion",
               "limitations_stated", "funding", "coi", "ref_check"]
# 陣列欄位(頂層 key: [ ... ] 單行)
LIST_KEYS = ["instruments", "statistics", "tags"]
# 第二層:JSON 鍵 → (父區塊, 子鍵)
NESTED = {
    "pico": ("pico", "ai_draft"),
    "key_findings": ("key_findings", "ai_draft"),
    "gap": ("gap", "ai_draft"),
    "rob": ("rob", "ai_draft"),
    "rob_tool": ("rob", "tool"),
    # Phase 6
    "grade": ("grade", "ai_draft"),
    "grade_certainty": ("grade", "certainty"),
    "spin": ("spin", "ai_draft"),
}


def yaml_str(s):
    """單行雙引號字串,換行壓成空白,雙引號改單引號避免破壞 YAML。"""
    s = re.sub(r"\s*\n\s*", " ", str(s)).strip()
    return '"' + s.replace("\\", "\\\\").replace('"', "'") + '"'


def yaml_list(items):
    return "[" + ", ".join(yaml_str(x) for x in items) + "]"


def split_frontmatter(text):
    m = re.match(r"^---\n(.*?\n)---\n(.*)$", text, re.DOTALL)
    if not m:
        raise SystemExit("✗ 找不到 frontmatter(檔案開頭需為 ---)。")
    return m.group(1), m.group(2)


def apply(fm_lines, data):
    """逐行更新 frontmatter。回傳 (新行list, 已更新欄位list)。"""
    out, updated = [], []
    parent = None  # 目前所在的第二層父區塊
    for line in fm_lines:
        stripped = line.rstrip("\n")

        # 追蹤父區塊:頂層(無縮排)且以 : 結尾且無值 → 進入區塊
        top = re.match(r"^([a-z_]+):\s*$", stripped)
        if top:
            parent = top.group(1)
            out.append(line)
            continue
        if re.match(r"^[a-z_]+:", stripped):  # 其他頂層鍵 → 離開區塊
            parent = None

        # 頂層純量
        m = re.match(r"^([a-z_]+):\s", stripped)
        if m and parent is None:
            key = m.group(1)
            if key in SCALAR_KEYS and key in data and data[key] not in (None, ""):
                out.append(f"{key}: {yaml_str(data[key])}\n")
                updated.append(key)
                continue
            if key in LIST_KEYS and key in data and data[key]:
                out.append(f"{key}: {yaml_list(data[key])}\n")
                updated.append(key)
                continue

        # 第二層子鍵(縮排兩格),依 parent 決定要不要更新
        sub = re.match(r"^  (ai_draft|tool|certainty):\s", stripped)
        if sub and parent:
            child = sub.group(1)
            # 找出對應此 (parent, child) 的 JSON 鍵
            for jkey, (p, c) in NESTED.items():
                if p == parent and c == child and jkey in data and data[jkey] not in (None, ""):
                    out.append(f"  {child}: {yaml_str(data[jkey])}\n")
                    updated.append(f"{parent}.{child}")
                    break
            else:
                out.append(line)
            continue
        # confirmed 子鍵一律原樣保留(絕不覆蓋人工確認)
        out.append(line)
    return out, updated


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    md_path, json_arg = sys.argv[1], sys.argv[2]
    raw = sys.stdin.read() if json_arg == "-" else open(json_arg, encoding="utf-8").read()
    data = json.loads(raw)

    with open(md_path, encoding="utf-8") as f:
        text = f.read()
    fm, body = split_frontmatter(text)
    fm_lines = fm.splitlines(keepends=True)
    new_lines, updated = apply(fm_lines, data)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("---\n" + "".join(new_lines) + "---\n" + body)

    if updated:
        print(f"✓ 已更新 {len(updated)} 個欄位:{', '.join(updated)}")
    else:
        print("⚠ 沒有可更新的欄位(JSON 為空或鍵名不符)。")
    print(f"  檔案:{md_path}(confirmed / 內文未更動)")


if __name__ == "__main__":
    main()
