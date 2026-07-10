# 用 Obsidian 編輯(回自己電腦時的深度整理)

Decap 適合「任何電腦、純網頁快速確認」;Obsidian 適合「自己電腦、關聯圖與深度整理」。
兩者編輯的是**同一批** `src/content/articles/*.md`,不衝突(別在兩處同時改同一篇即可)。

## 設定(逐步)

1. 下載安裝 Obsidian:<https://obsidian.md/download>(免費)。
2. 先把 repo clone 到本機(若還沒):
   ```bash
   git clone https://github.com/LukeHsiao-YC/nutrition_study.git
   ```
3. Obsidian 開啟 → **Open folder as vault** → 選 repo 根目錄
   → 若問「信任作者」按 **Trust author and enable plugins**。
   （本 repo 已附 `.obsidian/app.json`,自動排除 node_modules/dist 等雜訊。)
4. 裝外掛:**Settings → Community plugins → Turn on** → **Browse**,搜尋並安裝+啟用:
   - **Dataview**:把 frontmatter 變成即時表格(儀表板用)。
   - **Obsidian Git**:自動定時 commit/push,換電腦不漏同步。
   - **Templater**(選用):用 [`templates/paper.md`](../templates/paper.md) 快速新建論文。
5. 打開 **`notes/研究儀表板.md`** —— 已內建好 5 個 Dataview 查詢(待確認、依證據等級、
   依主題、各期刊篇數、已完成),裝好 Dataview 後立刻就有互動表格。

## 關聯圖(Graph view)

- 左側工具列開 **關聯圖檢視**。
- 右上齒輪 → 打開 **「標籤(Tags)」** → 共用標籤的論文會自動群聚,一眼看出主題群與研究缺口。
- 想手動連兩篇相關論文:在筆記裡用 `[[檔名]]` 互連(例如 `[[38572369]]`),關聯圖就會連起來。

## Dataview:改查詢

儀表板裡的查詢可自由改 `WHERE`/`SORT`。例:只看高證據等級 → `WHERE grade.certainty = "High"`;
只看 RCT → `WHERE contains(study_design, "randomi")`。可用欄位:`depth` `journal` `study_design`
`sample_size` `grade.certainty` `rob.tool` `tags` `pico.confirmed` 等(巢狀欄位用點號)。

## 注意

- `.obsidian/` 的工作區快取與下載的外掛已被 `.gitignore` 排除,只有共用設定 `app.json` 進版控。
- 深讀論文的「原文全文」很長屬正常;那是給萃取用的原始文字。
- Obsidian 與 Decap `/admin/` 編輯的是同一批 md,別在兩處同時改同一篇即可。
