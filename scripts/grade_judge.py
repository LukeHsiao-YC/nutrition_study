#!/usr/bin/env python3
"""GRADE 證據等級 — 用算術而非「感覺」決定(Phase 6)

語言模型只負責替五個 GRADE 面向評級(not_serious / serious / very_serious),
本程式「確定性地」重算最終證據等級,並強制 GRADE 規則。模型自報的等級僅供參考;
以本程式算出的為準,兩者不一致時警告。純 Python 3 標準庫,無相依、無網路。

靈感來源:drpwchen/claude-paper-tools 的 grade_judge.py(MIT),此為獨立重寫。

輸入(JSON,stdin 或檔案):
{
  "starting_level": "high",          # high(RCT)/ low(觀察性研究)
  "domains": [                        # 五個降級面向
    {"name":"risk_of_bias","rating":"serious"},
    {"name":"inconsistency","rating":"not_serious"},
    {"name":"indirectness","rating":"not_serious"},
    {"name":"imprecision","rating":"serious"},
    {"name":"publication_bias","rating":"not_serious"}
  ],
  "upgrades": [                       # 選填,僅觀察性研究、且無任何降級時可用
    {"name":"large_effect","rating":"serious"}     # serious=+1, very_serious=+2
  ],
  "model_reported": "low"            # 選填:模型自報等級,用來比對
}

用法:  echo '{...}' | python3 scripts/grade_judge.py -
       python3 scripts/grade_judge.py input.json
"""
import json
import sys

LEVELS = ["Very low", "Low", "Moderate", "High"]  # 1..4
NAME_TO_IDX = {"very low": 0, "low": 1, "moderate": 2, "high": 3}
DOWN = {"not_serious": 0, "serious": 1, "very_serious": 2}
UP = {"not_serious": 0, "serious": 1, "very_serious": 2}


def norm_level(s):
    return NAME_TO_IDX.get(str(s).strip().lower().replace("_", " "), None)


def judge(data):
    warnings = []
    start = norm_level(data.get("starting_level", "high"))
    if start is None:
        raise SystemExit("✗ starting_level 需為 high/moderate/low/very low")
    is_obs = start <= 1  # low 起始 = 觀察性研究

    downgrades = 0
    for d in data.get("domains", []):
        r = str(d.get("rating", "not_serious")).strip().lower()
        if r not in DOWN:
            warnings.append(f"未知的 domain rating:{r}(當作 not_serious)")
        downgrades += DOWN.get(r, 0)

    upgrades = 0
    for u in data.get("upgrades", []):
        r = str(u.get("rating", "not_serious")).strip().lower()
        upgrades += UP.get(r, 0)

    # GRADE 規則:只有觀察性研究可升級;且任何降級後不得升級
    if upgrades and not is_obs:
        warnings.append("非觀察性研究不得升級,已忽略升級。")
        upgrades = 0
    if upgrades and downgrades:
        warnings.append("已有降級,依 GRADE 不得再升級,已忽略升級。")
        upgrades = 0

    final = max(0, min(3, start - downgrades + upgrades))
    result = {
        "starting_level": LEVELS[start],
        "downgrades": downgrades,
        "upgrades": upgrades,
        "certainty": LEVELS[final],
        "warnings": warnings,
    }

    reported = data.get("model_reported")
    if reported is not None:
        ri = norm_level(reported)
        if ri is None:
            warnings.append(f"model_reported 無法解析:{reported}")
        elif ri != final:
            warnings.append(
                f"⚠ 模型自報「{LEVELS[ri]}」與算出的「{LEVELS[final]}」不一致,以算出者為準。"
            )
    return result


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    raw = sys.stdin.read() if sys.argv[1] == "-" else open(sys.argv[1], encoding="utf-8").read()
    res = judge(json.loads(raw))
    print(json.dumps(res, ensure_ascii=False, indent=2))
    # 有警告時 exit 2,方便自動化察覺不一致
    sys.exit(2 if res["warnings"] else 0)


if __name__ == "__main__":
    main()
