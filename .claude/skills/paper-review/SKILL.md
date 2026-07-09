---
name: paper-review
description: 對一篇論文做期刊討論會等級的批判性評讀(能不能信?做得好不好?)。依設計路由 RoB 工具、用 grade_judge.py 確定性算 GRADE 證據等級、用 argdown_lint.py 抓過度推論/spin、可對引用清單做 CrossRef 存在性驗證。當使用者說「評讀這篇」「paper review」「這篇可信嗎」「critical appraisal」「跑 GRADE」或指向某篇要嚴格評讀時使用。與 extract-paper(內容 digest)分工:這支回答「可信度」。
---

# paper-review:批判性評讀

回答「**這篇能不能信?做得好不好?**」。核心原則沿用 drpwchen/claude-paper-tools 的精神:
**語言模型做語意判斷,確定性程式做邏輯與算術**——證據等級與過度推論不靠感覺,靠程式把關。

## 硬性前提:必須有全文
先確認目標文章 body 有「## 原文全文」且非只有摘要(`fulltext_source` 不是空/none)。
**只有摘要就停手**,回報「無全文,無法做可信賴的評讀,請先用 ingest 取全文」。不做「摘要級假評讀」。

## 步驟

### 1. 依研究設計路由 RoB 工具(選對工具,不是一張清單打天下)
| 研究設計 | 工具 |
|---|---|
| RCT | Cochrane RoB 2 |
| 世代 / 病例對照 | ROBINS-I 或 Newcastle-Ottawa |
| 橫斷 | Newcastle-Ottawa(改編)/ AXIS |
| 系統回顧 / 統合分析 | AMSTAR-2 +（逐結果)GRADE + PRISMA 2020 報告查核 |
| 診斷準確性 | QUADAS-2 |
| 預測模型 | PROBAST |
| 臨床指引 | AGREE II |
| 敘事回顧 | SANRA + 選擇性引用(cherry-picking)查核 |
| 個案系列 / 報告 | JBI checklist |
| 研究計畫(protocol) | 無結果不評分;檢查註冊、預先分析計畫、CONSORT/SPIRIT |

觀察性研究另檢視是否違反基本因果推論原則(混雜校正是否足夠、時序、選樣偏誤、immortal time bias 等)。

### 2. GRADE 證據等級(確定性計算,不可自己喊)
- 替五個面向評級:risk_of_bias / inconsistency / indirectness / imprecision / publication_bias(not_serious / serious / very_serious)。
- RCT 起始 high、觀察性起始 low;觀察性可依 large_effect / dose_response / plausible_confounding 升級(但任何降級後不得升級)。
- **執行**:把評級組成 JSON 交給程式重算,不要自己心算等級:
  ```bash
  echo '{"starting_level":"high","domains":[...],"model_reported":"<你的直覺等級>"}' | python3 scripts/grade_judge.py -
  ```
  以程式輸出的 `certainty` 為準;若有 warning(與你直覺不一致)要在草稿中說明。

### 3. 論證 / spin 稽核(抓過度推論)
- 取論文的主要結論,替每個支持論點標前提類型(direct_rct / association / surrogate_outcome / single_study / subgroup / secondary_outcome / mechanistic / expert_opinion),並標主張類型(hard_endpoint / causal / benefit / association / descriptive)。
- **執行**:
  ```bash
  echo '{"claims":[{"claim":"...","claim_type":"...","premises":[{"id":"P1","type":"..."}]}]}' | python3 scripts/argdown_lint.py -
  ```
  把回報的 gaps 寫進 spin 草稿(例:替代終點→硬終點、相關→因果、次組→療效)。沒有 gap 就寫「未發現明顯過度推論」。

### 4. 引用清單 CrossRef 驗證(有引用時)
- 若原文全文含參考文獻,抽數筆關鍵引用的 DOI,逐筆 `python3 scripts/ingest.py doi <DOI>` 驗證存在且標題相符。
- 摘要寫進 `ref_check`(例:「抽驗 8 筆,7 筆吻合,1 筆 DOI 查無—疑似錯誤」)。查不到就明說,不要靜默略過。

### 5. 寫回(用 helper,勿手改 YAML)
把結果整理成 JSON,鍵:`grade_certainty`(程式算出的等級)、`grade`(五面向理由)、`spin`、`ref_check`,交給:
```bash
python3 scripts/apply_extraction.py <檔案> - <<'JSON'
{ "grade_certainty":"Low", "grade":"...", "spin":"...", "ref_check":"..." }
JSON
```
（同時可一併寫 rob_tool/rob。)這些寫進 `ai_draft`/`certainty`,**不碰 confirmed**。

## 回報原則
- 每個做過的查核給結論;**每個失敗的查核明列為 gap**(「PubPeer 查核:失敗/無結果」),不得靜默當成「沒問題」。
- 結尾提醒使用者到 `/admin/` 逐項確認,並強調:GRADE 等級以 grade_judge.py 為準、spin 以 argdown_lint.py 為準。
- 不是醫療建議、不取代讀原文;這是「拒絕讓看似合理但錯誤的評讀過關」的第二讀者。
