# 用 Obsidian 編輯(回自己電腦時的深度整理)

Decap 適合「任何電腦、純網頁快速確認」;Obsidian 適合「自己電腦、關聯圖與深度整理」。
兩者編輯的是**同一批** `src/content/articles/*.md`,不衝突(別在兩處同時改同一篇即可)。

## 設定

1. 先把 repo clone 到本機(若還沒):
   ```bash
   git clone https://github.com/LukeHsiao-YC/nutrition_study.git
   ```
2. Obsidian → **Open folder as vault** → 選 repo 根目錄。
3. 建議外掛(Community plugins):
   - **Obsidian Git**:自動定時 commit/push,換電腦不漏同步。
   - **Dataview**:把 frontmatter 查詢成表格(見下方範例),追蹤哪些還沒確認。
   - **Templater**(選用):用 [`templates/paper.md`](../templates/paper.md) 快速新建深讀論文。

## 關聯

`related` 與內文用 `[[PMID]]` 互連(例如 `[[42401201]]`),因為深讀檔名就是 PMID,
Obsidian 的 wikilink 與關聯圖(Graph view)會自動連起來。

## Dataview 範例:待確認清單

在任一筆記貼上以下區塊,即時列出「深讀中但還有欄位沒確認」的論文:

````markdown
```dataview
TABLE journal AS 期刊, study_design AS 設計, depth AS 階段
FROM "src/content/articles"
WHERE depth = "reading" AND (pico.confirmed = "" OR key_findings.confirmed = "")
SORT pubDate DESC
```
````

## 注意

- `.obsidian/` 的工作區快取已被 `.gitignore` 排除,不會污染 repo。
- 深讀論文的「原文全文」很長屬正常;那是給萃取用的原始文字。
