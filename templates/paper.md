---
# ══════════════════════════════════════════════════════════════
# 深讀道論文模板 — 複製此檔到 src/content/articles/ 後填寫
# 快速道(摘要級)由抓取腳本自動產生,不需要用這個模板
# ══════════════════════════════════════════════════════════════

# ── 基本資訊(第一層:高信賴)──
title: ""
journal: ""
category: "未分類"          # 兒童肥胖 / 營養衛教介入 / 社區營養 / 營養流行病學 / 營養評估
pubDate: ""                # YYYY-MM-DD
link: ""
doi: ""
pmid: ""
tags: []
authors: []               # 作者(Crossref 自動填,供 BibTeX/RIS 匯出)

# ── 狀態機 ──
depth: "reading"            # triage(摘要) → reading(全文萃取中) → done(已確認)
fulltext_source: "upload"   # pmc / upload / unpaywall / none

# ── 第一層:高信賴,可由全文自動填入 ──
study_design: ""            # 如 RCT / cohort / cross-sectional / systematic review
sample_size: ""
inclusion: ""
exclusion: ""
instruments: []             # 使用的量表/工具,如 [PHQ-9, FFQ]
statistics: []              # 統計方法,如 [mixed-effects model, logistic regression]
limitations_stated: ""      # 作者自陳的研究限制
funding: ""                 # 資助來源
coi: ""                     # 利益衝突揭露

# ── 第二層:AI 產草稿 → 你審閱後填 confirmed(空=尚未確認)──
pico:
  ai_draft: ""
  confirmed: ""
rob:
  tool: ""                  # Cochrane-RoB2 / Newcastle-Ottawa / JBI ...
  ai_draft: ""
  confirmed: ""
key_findings:
  ai_draft: ""
  confirmed: ""
gap:
  ai_draft: ""
  confirmed: ""

# ── Phase 6:批判性評讀(paper-review skill 產生)──
grade:
  certainty: ""             # Very low / Low / Moderate / High(由 grade_judge.py 算)
  ai_draft: ""              # GRADE 五面向理由
  confirmed: ""
spin:
  ai_draft: ""              # argdown_lint.py 抓到的過度推論
  confirmed: ""
ref_check: ""               # 引用清單 CrossRef 驗證摘要

# ── 關聯與個人筆記 ──
related: []                 # 相關論文的 pmid,如 ["42401201"]
my_notes: ""                # 個人評語 / 延伸想法
---

## 核心發現

<!-- AI 草稿會放這裡,你可直接改寫 -->

## 證據等級 / 風險偏誤

<!-- 依 rob.tool 的評估工具逐項填寫,最後由你簽核 -->

## 延伸想法 / 研究缺口

## 與其他文獻的關聯

<!-- 用 [[pmid]] 連結,如 [[42401201]] -->

## 個人評語

## 原文資訊 (Original)

**Title:**
**Abstract:**
