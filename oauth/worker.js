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
      const status = ok ? 'success' : 'error';
      const payload = ok
        ? { token: data.access_token, provider: PROVIDER }
        : { error: data.error_description || data.error || 'no token' };
      const message = `authorization:${PROVIDER}:${status}:${JSON.stringify(payload)}`;

      const html = `<!doctype html><html><body><script>
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
