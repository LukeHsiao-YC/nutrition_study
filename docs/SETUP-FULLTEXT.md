# 取得論文全文的方法(路徑階梯)

概念取自 [paper-fetch](https://github.com/drpwchen/paper-fetch)(MIT):
**先試最便宜、最合法的路,失敗才往下**。分兩層,第 ① 層已內建、零設定。

```
DOI / PMID
 ├─ ① 開放取用(內建)── PMC 全文、Unpaywall、Semantic Scholar → 自動抓 PDF
 ├─ ② 出版商 TDM / 機構代理(選配)── 你自己的圖書館/金鑰(用 paper-fetch)
 └─ ③ 都失敗 ── 手動下載 PDF 丟進 pdfs/
```

## 第 ① 層:開放取用自動下載(已內建、免設定)

```bash
python3 scripts/ingest.py fetch 10.1186/s12889-023-15258-x   # 給 DOI 自動抓 OA 全文
python3 scripts/ingest.py pmc 38572369                        # 給 PMID 抓 PMC 全文
```
- `fetch` 會問 Unpaywall / Semantic Scholar 要開放取用 PDF 連結,逐一試抓,
  **驗 `%PDF` 開頭**(不信 Content-Type,擋掉付費牆回傳的假 HTML),成功就轉全文進料。
- Zotero `pull` 也已接上:非 PMC 的項目會自動用 DOI 試抓 OA。
- Email 預設用你的;要換設環境變數 `UNPAYWALL_EMAIL`。
- 涵蓋:PMC、Europe PMC、Cambridge、BMC、PLOS、機構典藏庫等的 OA 版本。

## 第 ② 層:付費論文(選配,需要你的設定)

有些論文只有付費全文。合法自動化的方式是**用你自己的訂閱**:
- 出版商 TDM API(Elsevier/Wiley/Springer,你自己註冊金鑰)
- 你學校圖書館的 EZproxy / 校外連線

這一塊 [paper-fetch](https://github.com/drpwchen/paper-fetch) 已做得很完整(20+ 出版商路徑),
**不建議自己重寫**。要用的話:
1. `git clone https://github.com/drpwchen/paper-fetch`,照它的 `config.yaml` 填你的
   Unpaywall email、(選填)出版商金鑰、你學校的圖書館代理端點。
2. 需要付費全文時:`python paper_fetch.py <DOI> out.pdf`,再把 `out.pdf` 丟進本專案 `pdfs/`
   跑 `ingest upload`。
> 注意:這是自動化「你本來就有權限」的存取,不是繞過付費牆,也不分享帳密。

## 第 ③ 層:手動

真的抓不到就自己下載 PDF 丟進 `pdfs/`,跑 `python3 scripts/ingest.py upload`。
