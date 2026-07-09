# nutrition_study · 研究所文獻工作流

從各大期刊定期抓取最新論文,做成**論文整理 / 研究撰寫 / 簡報製作 / 學術資料庫**的一站式工作流。
線上網址:<https://lukehsiao-yc.github.io/nutrition_study/>

---

## 這套系統怎麼運作(全貌)

分「**快速道**」與「**深讀道**」兩速,對應研究生真實行為——先大量掃、再深讀少數。

```
① 抓取(自動)   PubMed 排程 → Gemini 摘要速報   → 首頁近七日 / 每週彙整 / RSS
② 進料(挑選)   PDF 丟 pdfs/ 或 pmc <PMID>       → 全文(markitdown)+ DOI 驗證
③ 萃取(半自動) Claude Code「萃取這篇」          → 第一層填欄 + 第二層草稿
④ 確認(你)     Decap 純網頁 / Obsidian          → 填 confirmed、寫評語
⑤ 產出          文獻矩陣 / BibTeX→Zotero          → 投影片(NotebookLM 或 Marp)
```

- **快速道**:所有論文都有,只到摘要層級,用來 triage。
- **深讀道**:你挑出的少數,取全文 → 結構化研究卡(基本資訊 + PICO + 證據等級 + 核心發現)。
- **資料即真相**:所有東西都是 `src/content/articles/*.md`(YAML frontmatter + 內文),
  網站、Decap、Obsidian、腳本都讀同一批檔,不被任何平台鎖住。

---

## 網站頁面

| 頁面 | 網址 | 用途 |
|---|---|---|
| 首頁 | `/` | 近七日速報、星號收藏、標籤 |
| 深讀庫 | `/deepread` | 文獻矩陣橫向比較 + 研究卡 + 待確認標示 |
| 每週彙整 | `/digest` | 依週分組的新文獻 + 匯出入口 |
| 歷史文獻庫 | `/archive` | 全部文獻 + 全文搜尋(Pagefind) |
| 論文詳情 | `/paper/<slug>` | 研究卡、引用匯出、相關文獻、全文 |
| 管理後台 | `/admin/` | Decap CMS 純網頁編輯(需先設定 OAuth) |
| RSS | `/rss.xml` | 訂閱新文獻 |
| 引用匯出 | `/library.bib`、`/library.ris` | 全站一次匯出 |

---

## 日常操作

### A. 深讀一篇論文(核心流程)

1. **取得全文**
   - 自己上傳:把 PDF 丟進 `pdfs/`(此資料夾不進版控),然後:
     ```bash
     python3 scripts/ingest.py upload            # 處理 pdfs/ 全部
     python3 scripts/ingest.py upload path.pdf   # 指定單一檔
     ```
     檔名建議用 PMID(如 `42401201.pdf`)。
   - 開放取用(免下載):
     ```bash
     python3 scripts/ingest.py pmc 42401201     # 用 PMID 抓 PMC 全文
     ```
   會產生 `src/content/articles/<id>.md`,`depth: reading`,全文放在內文、DOI 經 Crossref 驗證。

2. **萃取**(在此資料夾開 Claude Code)
   > 對 Claude 說:「萃取 src/content/articles/42401201.md」
   會自動填第一層欄位(設計/樣本/收案排除/量表/統計/限制/COI)、
   產第二層草稿(PICO、核心發現、RoB、研究缺口)。**AI 產的都放 `ai_draft`,不碰 `confirmed`。**

3. **確認**:逐項看 `ai_draft`,把你認可/修訂的內容填進 `confirmed`,完成後把 `depth` 改成 `done`。
   - 純網頁:`/admin/`(見下方設定)
   - 本機:Obsidian(見 [docs/OBSIDIAN.md](docs/OBSIDIAN.md))

4. **產出**
   - 引用:詳情頁「複製 BibTeX」或下載 `.bib`/`.ris` → Zotero / Word / LaTeX
   - 投影片:對 Claude 說「把這篇做成投影片」(串 NotebookLM),
     或離線:`python3 scripts/paper_to_marp.py src/content/articles/42401201.md`

### ⚡ 更省事:自動化這條流程

不想一步步跑的話,有兩種一鍵/零接觸方式:

- **`/process-pdfs`(推薦,免額外費用)**:把 PDF 丟進 `pdfs/`,在此資料夾開 Claude Code
  打 `/process-pdfs`,會自動「進料 → 萃取第一/二層 → build → commit → push」。品質最佳。
- **`autopilot.py`(真・零接觸,用 Gemini)**:需先設 `GEMINI_API_KEY`(export 或放 `.env`)。
  ```bash
  python3 scripts/autopilot.py --push     # 進料+Gemini 萃取+commit/push
  python3 scripts/autopilot.py --watch     # 監看 pdfs/,丟檔即自動處理
  ```
  免打指令,但萃取品質略低、會用 Gemini 額度。

兩種產出的第二層都仍是 `ai_draft`,最後由你到 `/admin/` 確認、填 `confirmed`。

### B. 手動加一篇(不經抓取)

複製 [`templates/paper.md`](templates/paper.md) 到 `src/content/articles/`,填 frontmatter 後同上萃取。

---

## 一次性設定(只有你能做)

### 1. 開啟網站部署
GitHub repo → **Settings → Pages → Source** 設為 **GitHub Actions**。
之後每次 push 到 `main`,`.github/workflows/deploy.yml` 會自動建置(含 Pagefind 索引)並部署。

### 2. 啟用純網頁編輯後台(Decap CMS)
照 [docs/SETUP-CMS.md](docs/SETUP-CMS.md):建 GitHub OAuth App → 部署 Cloudflare Worker →
把 `public/admin/config.yml` 的 `base_url` 換成你的 Worker 網址。完成後 `/admin/` 用 GitHub 登入即可編輯。

---

## 本機開發

```bash
npm install            # 安裝(首次)
pip install -r requirements.txt   # 安裝 Python 相依(ingest / slides)
npm run dev            # 本機預覽 http://localhost:4321/nutrition_study/
npm run build          # 建置 + Pagefind 索引到 dist/
```

---

## 目錄結構

```
scripts/
  fetch_papers.py      抓取(PubMed → Gemini 摘要,由 update.yml 排程)
  ingest.py            進料(PDF/PMC → 全文 + Crossref 驗證)
  apply_extraction.py  把萃取 JSON 安全寫回 frontmatter(不碰 confirmed/內文)
  paper_to_marp.py     論文 → Marp 投影片(離線)
src/
  content/articles/    論文(單一真相來源)
  content/config.ts    frontmatter schema
  components/ResearchCard.astro   研究卡
  lib/cite.ts          BibTeX / RIS 產生器
  pages/               首頁 / 深讀庫 / 每週彙整 / 詳情頁 / 匯出 / RSS
.claude/skills/
  extract-paper/       萃取 skill(第一/二層 + 自我測驗卡)
  paper-review/        批判性評讀 skill(GRADE + spin + 引用驗證)
  paper-to-slides/     投影片 skill(串 notebooklm-research)
scripts/
  grade_judge.py       確定性計算 GRADE 證據等級(LLM 評級 → 程式重算)
  argdown_lint.py      確定性抓過度推論 / spin
public/admin/          Decap CMS 後台
oauth/worker.js        Decap OAuth 用的 Cloudflare Worker
docs/                  SETUP-CMS.md / OBSIDIAN.md
templates/paper.md     深讀論文模板
```

## frontmatter 欄位速查

- **基本**:`title` `authors` `journal` `category` `pubDate` `link` `doi` `pmid` `tags`
- **狀態**:`depth`(triage / reading / done)、`fulltext_source`
- **第一層(高信賴)**:`study_design` `sample_size` `inclusion` `exclusion` `instruments` `statistics` `limitations_stated` `funding` `coi`
- **第二層(AI 草稿→你確認)**:`pico` `rob`(含 `tool`)`key_findings` `gap`,各含 `ai_draft` / `confirmed`
- **個人**:`related`(PMID 互連)`my_notes`

> 研究誠信:AI 只填有原文證據的內容,查無則留白;`confirmed` 永遠只由你本人填寫。
