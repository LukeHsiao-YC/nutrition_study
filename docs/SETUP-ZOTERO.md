# Zotero 雙向同步設定

讓你的深讀道論文與 Zotero 書目庫互通:
- **push**:本地論文 → Zotero(自動建立條目、帶標籤與 GRADE)
- **pull**:Zotero(你在 Zotero 加的論文)→ 本地(有 PMID 就自動抓 PMC 全文)

## 一次性設定

1. 取得金鑰與 userID:<https://www.zotero.org/settings/keys>
   - 按 **Create new private key**,勾選 **Allow library access**(讀寫)→ 建立 → 複製金鑰。
   - 同頁上方的 **Your userID**(一串數字)記下來。
2. 寫進專案根目錄 `.env`(已 gitignore):
   ```
   ZOTERO_API_KEY=你的金鑰
   ZOTERO_USER_ID=你的userID
   ZOTERO_COLLECTION=       # 選填:只同步某 collection 的 key(留空=整個 library)
   ```
   > collection key:在 Zotero 網頁版打開該分類,網址 `.../collections/XXXXXXX` 那段。

3. 安裝相依(若還沒):`pip install -r requirements.txt`

## 使用

```bash
python3 scripts/zotero_sync.py push     # 本地 → Zotero
python3 scripts/zotero_sync.py pull     # Zotero → 本地
python3 scripts/zotero_sync.py sync     # 先 pull 再 push
```

## 運作方式與限制

- **去重以 DOI 為準**:兩邊已有相同 DOI 就不重建。
- **push** 會帶上標題/作者/期刊/年份/DOI/標籤,`extra` 欄放 PMID 與 GRADE 等級。
- **pull** 對「Zotero 有、本地沒有」的項目:
  - 有 PMID → 自動 `ingest.py pmc` 抓 PMC 開放全文。
  - 只有 DOI、無全文 → 提示你手動上傳 PDF 後再 ingest(靜態站無法自動取得付費全文)。
- 匯入後記得跑萃取/評讀(`/process-pdfs` 或 `autopilot.py`)把研究卡補齊。
