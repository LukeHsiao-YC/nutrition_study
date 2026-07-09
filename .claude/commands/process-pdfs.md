---
description: 自動處理 pdfs/ 內所有新論文:進料(markitdown+DOI)→ 萃取(第一/二層)→ commit
---

一鍵處理使用者丟進 `pdfs/` 的論文。請依序執行,全程不需再問使用者:

1. 執行進料:`python3 scripts/ingest.py upload`
   - 若沒有新 PDF 就回報「pdfs/ 沒有待處理的檔案」並結束。
2. 找出所有 `depth: reading` 且第二層 `pico.ai_draft` 仍為空的文章(通常就是剛進料的)。
3. 對每一篇,套用 **extract-paper** skill 的規則:
   - 讀「## 原文全文」全文。
   - 依 EBM 規則整理出萃取 JSON(第一層欄位 + 第二層 pico/rob/key_findings/gap 的 ai_draft;
     RoB 依設計選工具;只寫有原文證據的內容,查無留白;數字逐字對照)。
   - 用 `python3 scripts/apply_extraction.py <檔案> <暫存JSON>` 寫回(不要手改 YAML)。
   - protocol / 無結果的論文,核心發現要誠實標註「尚無結果」,不得捏造。
4. 全部處理完後:
   - `npm run build` 確認站台可建置(有錯要修到過)。
   - `git add -A`、commit(訊息列出新增/更新了哪幾篇)、`git push origin main`。
     若 push 被拒,先 `git pull --rebase origin main` 再 push。
5. 最後回報:處理了哪幾篇、各篇的研究設計與待確認狀態,並提醒使用者到
   `/admin/`(Decap)或 Obsidian 逐項確認 ai_draft、填入 confirmed。

注意:PDF 本身不進版控(pdfs/ 已 gitignore),只 commit 產出的 .md。
一次處理多篇時逐篇萃取,不要略過任何一篇。
