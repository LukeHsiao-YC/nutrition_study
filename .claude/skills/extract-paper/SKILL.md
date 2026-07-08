---
name: extract-paper
description: 讀深讀道文章的原文全文,自動填第一層高信賴欄位、產第二層 ai_draft 草稿(PICO/RoB/核心發現/研究缺口),寫回 frontmatter。當使用者說「萃取這篇」「extract paper」「填研究卡」「跑 extract-paper」或指向 src/content/articles 下 depth:reading 的文章時使用。
---

# extract-paper:深讀道論文萃取

把一篇已含「原文全文」的深讀道文章,轉成結構化研究卡。**只產出證據支持的內容,絕不編造**。

## 適用對象
`src/content/articles/*.md` 中 `depth: reading`、body 有「## 原文全文 (Full text)」區塊的文章(由 `scripts/ingest.py` 產生)。若使用者沒指定檔案,列出所有 `depth: reading` 且第二層 `ai_draft` 仍為空的文章請他選。

## 鐵則(研究誠信)
1. **只根據原文全文**。全文找不到的欄位一律留空字串,**不要用常識或訓練記憶補**。
2. 數字(樣本數、p 值、效應量)**逐字對照原文**,不確定就留空並在回報時說明。
3. **第一層 = 高信賴、可直接填**;**第二層 = 草稿**,寫進 `ai_draft`,**絕不碰 `confirmed`**(那是使用者的欄位)。
4. 全文若只有摘要(fulltext_source 顯示不完整),明確告訴使用者「此為摘要級萃取,樣本數/統計/RoB 可信度低」。

## 第一層欄位(填入 frontmatter,高信賴)
- `study_design`:如 randomized controlled trial / prospective cohort / cross-sectional / systematic review / case-control。用原文用詞。
- `sample_size`:總 N(必要時分組,如 "240 (I=120, C=120)")。
- `inclusion` / `exclusion`:收案與排除條件。
- `instruments`:量表/工具陣列(如 ["FFQ","PHQ-9"])。
- `statistics`:統計方法陣列(如 ["mixed-effects model","ITT"])。
- `limitations_stated`:**作者自陳**的限制(通常在 Discussion/Limitations 段)。
- `funding` / `coi`:資助來源與利益衝突(通常有固定 disclosure 段)。
- `tags`:3–5 個繁中主題標籤(沿用既有慣例,如 兒童肥胖、營養衛教介入)。

## 第二層草稿(寫入各自的 ai_draft)
- `pico`:P/I/C/O 逐項;觀察性研究可改寫成 PECO 或 Exposure–Outcome。
- `key_findings`:2–4 句核心發現,**帶關鍵數字**(效應量、CI、p)。
- `gap`:研究缺口 / 未來方向。
- `rob_tool` + `rob`:依設計選對工具並簡評——
  - RCT → **Cochrane RoB 2**(隨機、分配隱匿、盲性、失訪、選擇性報告)
  - 世代/病例對照 → **Newcastle-Ottawa Scale**(選樣、可比性、暴露/結果測量)
  - 系統回顧 → **AMSTAR-2** / 觀察性亦可 JBI
  - `rob` 寫 2–4 句判斷 + 整體評級(low / some concerns / high 或 NOS 星等),並點出**最影響結論的偏誤來源**。

## 工作流程
1. 讀目標檔的「## 原文全文」全文。
2. 依上面規則整理出一份 JSON(只放有證據的鍵,值為字串;陣列用陣列):
   ```json
   {
     "study_design": "...", "sample_size": "...",
     "inclusion": "...", "exclusion": "...",
     "instruments": ["..."], "statistics": ["..."],
     "limitations_stated": "...", "funding": "...", "coi": "...",
     "tags": ["...","..."],
     "pico": "P: ... I: ... C: ... O: ...",
     "key_findings": "...(帶數字)",
     "gap": "...",
     "rob_tool": "Cochrane-RoB2",
     "rob": "...簡評 + 整體評級"
   }
   ```
3. 用 helper 安全寫回(**不要手改 YAML**,交給腳本以免格式錯亂):
   ```bash
   python scripts/apply_extraction.py <檔案路徑> - <<'JSON'
   { ...上面的 JSON... }
   JSON
   ```
4. 回報:條列填了哪些、哪些留空(缺證據)、以及 RoB 的整體評級。**提醒使用者逐項檢查 ai_draft 後,把認可的內容填進對應的 `confirmed`,再把 `depth` 改成 `done`。**

## 注意
- 一次只處理一篇;多篇就逐篇跑,每篇跑完各自回報。
- 若全文含大量參考文獻雜訊,以 Methods/Results/Discussion 段為準。
- 不修改 body 的敘述區塊(核心發現/個人評語那些標題),那是給使用者手寫的;結構化結論放 frontmatter。
