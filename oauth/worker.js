// ────────────────────────────────────────────────────────────────
// Decap CMS ↔ GitHub OAuth 代理(Cloudflare Worker)
//
// 為什麼需要它:GitHub Pages 是靜態的,無法保管 OAuth client secret,
// 也無法把「授權碼」換成「access token」。這個 Worker 就是做這一步。
//
// 部署方式見 docs/SETUP-CMS.md。需在 Worker 設定兩個環境變數(Secrets):
//   GITHUB_CLIENT_ID      GitHub OAuth App 的 Client ID
//   GITHUB_CLIENT_SECRET  GitHub OAuth App 的 Client Secret
// ────────────────────────────────────────────────────────────────

const PROVIDER = 'github';

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // 1) Decap 導向這裡開始授權
    if (url.pathname === '/auth') {
      const redirectUri = `${url.origin}/callback`;
      const scope = url.searchParams.get('scope') || 'repo';
      const authorize = new URL('https://github.com/login/oauth/authorize');
      authorize.searchParams.set('client_id', env.GITHUB_CLIENT_ID);
      authorize.searchParams.set('redirect_uri', redirectUri);
      authorize.searchParams.set('scope', scope);
      authorize.searchParams.set('state', crypto.randomUUID());
      return Response.redirect(authorize.toString(), 302);
    }

    // 2) GitHub 授權後帶 code 回來,這裡換 token 並回傳給 Decap
    if (url.pathname === '/callback') {
      const code = url.searchParams.get('code');
      if (!code) return new Response('Missing code', { status: 400 });

      const tokenRes = await fetch('https://github.com/login/oauth/access_token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          'User-Agent': 'decap-cms-oauth',
        },
        body: JSON.stringify({
          client_id: env.GITHUB_CLIENT_ID,
          client_secret: env.GITHUB_CLIENT_SECRET,
          code,
        }),
      });
      const data = await tokenRes.json();
      const ok = !!data.access_token;

      // 失敗:不 postMessage、不讓 Decap 關掉視窗,把原因大大地留在畫面上供診斷
      if (!ok) {
        const errHtml = `<!doctype html><html><body style="font-family:sans-serif;padding:32px;line-height:1.6;">
<h2 style="color:#c53030;">❌ 換 token 失敗</h2>
<p>GitHub 回傳:</p>
<pre style="background:#f7fafc;border:1px solid #e2e8f0;padding:12px;border-radius:6px;white-space:pre-wrap;">${JSON.stringify(data, null, 2)}</pre>
<p>把上面這段整個複製給協助你的人。此視窗<strong>不會自動關閉</strong>。</p>
</body></html>`;
        return new Response(errHtml, { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
      }

      // 成功:走 Decap 握手,自動關閉並登入
      const message = `authorization:${PROVIDER}:success:${JSON.stringify({ token: data.access_token, provider: PROVIDER })}`;
      const html = `<!doctype html><html><body style="font-family:sans-serif;padding:24px;">
<p>登入成功,視窗即將關閉…</p>
<script>
(function () {
  function receiveMessage(e) {
    window.opener.postMessage(${JSON.stringify(message)}, e.origin);
    window.removeEventListener('message', receiveMessage, false);
  }
  window.addEventListener('message', receiveMessage, false);
  window.opener.postMessage('authorizing:${PROVIDER}', '*');
})();
</script></body></html>`;

      return new Response(html, { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
    }

    return new Response('Decap CMS OAuth worker — 請從 CMS 的登入按鈕使用。', { status: 200 });
  },
};
