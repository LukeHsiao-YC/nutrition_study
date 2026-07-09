---
description: 對深讀道論文跑批判性評讀(GRADE + spin + RoB + 引用驗證),寫回研究卡
---

對指定論文(或所有已萃取但還沒評讀的深讀道文章)執行 **paper-review** skill:

1. 若使用者有指定檔案就處理那篇;否則找出 `src/content/articles/` 中
   `depth` 為 reading/done、body 有「## 原文全文」、但 `grade.certainty` 與
   `grade.ai_draft` 都還空的文章,列出來讓使用者選(或全部處理)。
2. 對每一篇,依 **paper-review** skill 的步驟:
   - **無全文就跳過並回報**(不做摘要級假評讀)。
   - 若該檔 frontmatter 缺 `grade:`/`spin:`/`ref_check:` 區塊,先補上空區塊
     (格式見 templates/paper.md),再往下。
   - 依研究設計路由 RoB 工具;protocol/無結果者不評分、改查註冊與預先分析計畫。
   - 替五個 GRADE 面向評級 → `python3 scripts/grade_judge.py -` 取確定性等級
     (protocol 無結果則 GRADE 標「不適用」、certainty 留空)。
   - 標主張前提類型 → `python3 scripts/argdown_lint.py -` 抓過度推論。
   - 有引用時抽數筆 DOI 以 `python3 scripts/ingest.py doi <DOI>` 驗證。
   - 用 `python3 scripts/apply_extraction.py <檔案> <JSON>` 寫回
     `grade_certainty`/`grade`/`spin`/`ref_check`(不碰 confirmed)。
3. 全部完成後 `npm run build` 驗證,再 `git add -A` → commit → `git push`
   (被拒先 `git pull --rebase`)。
4. 回報每篇的 GRADE 等級、spin 是否有 flag、以及失敗的查核(列為明確 gap)。
   提醒使用者:GRADE 以 grade_judge.py 為準、spin 以 argdown_lint.py 為準,
   到 /admin/ 逐項確認後填 confirmed。
