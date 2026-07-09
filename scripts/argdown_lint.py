#!/usr/bin/env python3
"""論證/spin 稽核 — 用規則抓「過度推論」(Phase 6)

語言模型把每個支持論點標上「前提類型」,本程式「確定性地」抓出不合法的推論跳躍
(把弱證據當強結論),不合格就 exit 1。純 Python 3 標準庫,無相依、無網路。

靈感來源:drpwchen/claude-paper-tools 的 argdown_lint.py(MIT),此為獨立重寫。

前提類型 premise.type:
  direct_rct, association, surrogate_outcome, single_study,
  subgroup, secondary_outcome, mechanistic, expert_opinion
主張類型 claim_type:
  hard_endpoint(硬終點/臨床結果), causal(因果), benefit(療效),
  association(相關), descriptive(描述)

輸入(JSON,單一主張或主張陣列):
  {"claim":"藥物降低骨折","claim_type":"hard_endpoint",
   "premises":[{"id":"P1","type":"surrogate_outcome"}]}
或 {"claims":[ {...}, {...} ]}

用法:  echo '{...}' | python3 scripts/argdown_lint.py -
"""
import json
import sys

STRONG = {"direct_rct"}  # 唯一能直接支撐因果/療效的前提
WEAK = {"association", "surrogate_outcome", "single_study",
        "subgroup", "secondary_outcome", "mechanistic", "expert_opinion"}
STRONG_CLAIMS = {"hard_endpoint", "causal", "benefit"}


def lint_one(claim):
    ptypes = [p.get("type", "") for p in claim.get("premises", [])]
    ctype = claim.get("claim_type", "")
    text = claim.get("claim", "")
    gaps = []

    def has(t):
        return t in ptypes

    def only(*ts):
        return ptypes and all(p in ts for p in ptypes)

    # 1) 強主張但完全沒有直接 RCT 支撐 → 過度推論
    if ctype in STRONG_CLAIMS and not has("direct_rct"):
        gaps.append(f"「{ctype}」等級的主張缺乏 direct_rct 支撐,僅靠 {sorted(set(ptypes))}")

    # 2) 替代終點 → 硬終點/療效
    if has("surrogate_outcome") and ctype in ("hard_endpoint", "benefit"):
        gaps.append("以替代終點(surrogate)推論硬終點/臨床療效")

    # 3) 相關 → 因果
    if only("association") and ctype in ("causal", "benefit", "hard_endpoint"):
        gaps.append("以相關性(association)推論因果")

    # 4) 單一研究 → 宣稱「一致/確立」
    if has("single_study") and any(k in text for k in ("一致", "確立", "consistently", "established", "證實")):
        gaps.append("以單一研究宣稱『一致/確立』")

    # 5) 只有次組/次要結果 → 療效主張(典型 spin)
    if only("subgroup", "secondary_outcome") and ctype in ("benefit", "hard_endpoint", "causal"):
        gaps.append("僅以次組/次要結果推論療效(典型 spin)")

    # 6) 只有機轉/專家意見 → 任何實證主張
    if only("mechanistic", "expert_opinion") and ctype in STRONG_CLAIMS:
        gaps.append("僅以機轉/專家意見支撐實證主張")

    return gaps


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    raw = sys.stdin.read() if sys.argv[1] == "-" else open(sys.argv[1], encoding="utf-8").read()
    data = json.loads(raw)
    claims = data.get("claims") if isinstance(data, dict) and "claims" in data else [data]

    total = 0
    report = []
    for c in claims:
        gaps = lint_one(c)
        total += len(gaps)
        report.append({"claim": c.get("claim", ""), "gaps": gaps, "ok": not gaps})

    out = {"total_gaps": total, "claims": report}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
