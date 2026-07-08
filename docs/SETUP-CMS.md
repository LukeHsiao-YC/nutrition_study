# Decap CMS(純網頁編輯後台)設定步驟

目標:任何電腦打開 `https://lukehsiao-yc.github.io/nutrition_study/admin/`,
用 GitHub 登入,就能編輯論文、填 `confirmed`、寫評語,存檔即 commit 回 repo。

需要一次性設定兩樣東西:**GitHub OAuth App** 與 **Cloudflare Worker**(免費)。

---

## 步驟 1 · 建立 GitHub OAuth App

1. 前往 GitHub → Settings → Developer settings → **OAuth Apps** → **New OAuth App**
   (網址:https://github.com/settings/developers)
2. 填寫:
   - **Application name**:`nutrition-study CMS`(隨意)
   - **Homepage URL**:`https://lukehsiao-yc.github.io/nutrition_study/`
   - **Authorization callback URL**:先隨便填 `https://example.com/callback`,
     等步驟 2 拿到 Worker 網址後回來改成 `https://<你的worker>.workers.dev/callback`
3. 建立後記下 **Client ID**,再按 **Generate a new client secret** 記下 **Client Secret**。

---

## 步驟 2 · 部署 Cloudflare Worker

1. 註冊/登入 Cloudflare(免費,免信用卡):https://dash.cloudflare.com
2. 左側 **Workers & Pages** → **Create** → **Create Worker** → 命名(如 `nutrition-cms-auth`)→ Deploy。
3. 進入該 Worker → **Edit code**,把 [`oauth/worker.js`](../oauth/worker.js) 的內容整段貼上 → **Deploy**。
4. 回 Worker 的 **Settings → Variables and Secrets**,新增兩個 **Secret**:
   - `GITHUB_CLIENT_ID` = 步驟 1 的 Client ID
   - `GITHUB_CLIENT_SECRET` = 步驟 1 的 Client Secret
   存檔後再 Deploy 一次。
5. 記下 Worker 網址,形如 `https://nutrition-cms-auth.<你的帳號>.workers.dev`。

---

## 步驟 3 · 回填設定

1. 回 **步驟 1** 的 OAuth App,把 **Authorization callback URL** 改成
   `https://<你的worker>.workers.dev/callback` 並儲存。
2. 編輯 [`public/admin/config.yml`](../public/admin/config.yml),把
   `base_url:` 改成你的 Worker 網址(**不含** `/callback`),例如:
   ```yaml
   base_url: https://nutrition-cms-auth.你的帳號.workers.dev
   ```
3. commit + push。Actions 部署後,打開
   `https://lukehsiao-yc.github.io/nutrition_study/admin/`,
   按 **Login with GitHub** → 授權 → 即可編輯。

---

## 常見問題

- **登入彈窗一閃就關、沒登入成功**:多半是 callback URL 或 Worker 的兩個 Secret 沒對。
  檢查 callback 結尾是 `/callback`、Secret 名稱完全一致。
- **權限太大不安心**:repo 是公開的話,可把 `oauth/worker.js` 的 `scope` 預設從
  `repo` 改成 `public_repo`,授權範圍較小。
- **存檔後 frontmatter 順序/引號變了**:正常。Decap 會重新序列化 YAML,
  Astro 照樣讀得懂,不影響網站。
- **想要更好的中文/介面**:可改用 Sveltia CMS(與此 `config.yml` 相容的直接替代),
  只需把 `index.html` 的 script 換成 Sveltia 的 CDN;Worker 同一個即可。
