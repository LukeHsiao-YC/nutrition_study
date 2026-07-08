---
name: paper-to-slides
description: 把深讀道論文做成投影片。優先串接 notebooklm-research skill 生成精美投影片(slide deck),或用離線 Marp 後備快速產出。當使用者說「這篇做成投影片」「做簡報」「paper to slides」「用 NotebookLM 做投影片」或指向 src/content/articles 下某篇論文要簡報時使用。
---

# paper-to-slides:論文轉投影片

把一篇論文(理想上是已萃取的深讀道文章)轉成報告用投影片。有兩條路:

## 路徑 A(預設):串 notebooklm-research 生成投影片
適合要精美、可直接報告的成品。

1. 讀目標論文 md;整理出要餵給 NotebookLM 的來源與重點:
   - 若已萃取:用 frontmatter 的 confirmed(優先)或 ai_draft(PICO、核心發現、RoB、gap)+ 第一層欄位。
   - 附上「原文全文」區塊或原文連結/DOI 作為來源。
2. 呼叫 **notebooklm-research** skill:
   - 建立 notebook,加入來源(原文全文文字,或 PubMed/DOI 連結)。
   - 產出 artifact 類型選 **slide deck**(投影片);可另加 study guide 供口頭報告。
   - 主題聚焦:研究問題→方法→核心發現(帶數字)→證據等級/偏誤→限制與缺口→臨床/研究意涵。
3. 把產出的投影片連結/檔案回報給使用者,並(若適用)存到 repo 的 `slides/` 或記錄於該論文的 `my_notes`。

## 路徑 B(後備):離線 Marp
不想依賴外部服務、或要快速草稿時:

```bash
python scripts/paper_to_marp.py src/content/articles/<檔名>.md
```
產生 `slides/<檔名>.md`(Marp 格式,含 PICO/方法/核心發現/RoB/缺口/評語/引用)。
再用 Marp for VS Code 或 `npx @marp-team/marp-cli slides/<檔名>.md --pdf`(或 `--pptx`)轉檔。

## 選擇建議
- 要交出去/口頭報告的正式簡報 → 路徑 A(NotebookLM,較精美、可加語音/測驗)。
- 自己 lab meeting 快速過、或離線 → 路徑 B(Marp,秒出、可版控)。

## 注意
- 投影片的內容以 **confirmed 為準**;若某欄還是 ai_draft(未確認),在產出時標註「(草稿,待核)」,避免把未經你確認的判斷當定論報出去。
- 數字與 RoB 評級必須與原文一致,不確定寧可略過。
