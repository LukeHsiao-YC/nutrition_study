把要深讀的論文 PDF 丟進這個資料夾,然後在專案根目錄執行:

    python scripts/ingest.py upload

它會用 markitdown 轉全文、Crossref 驗證 DOI,產生深讀道文章到 src/content/articles/。
檔名建議用該篇的 PMID(例如 42401201.pdf),會自動連結對應文章。

注意:此資料夾已被 .gitignore,PDF 不會進版控(避免版權與檔案大小問題)。
