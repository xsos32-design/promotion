/* r56→r229：頁面先抓網路最新版（3 秒沒回應才用手機存的版本）；圖片字型快取跨版本保留 */
const V = 'v2026-10-15-r240';
const P = self.registration.scope + '|';
const CORE = ['./', './index.html', './img/brand/hero.webp', './icon-192.png'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(P + 'core|' + V).then(c => c.addAll(CORE)).catch(() => {}).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith(P) && k !== P + 'rt' && !k.endsWith(V)).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const r = e.request;
  if (r.method !== 'GET') return;
  const u = new URL(r.url);
  const scope = new URL(self.registration.scope);
  if (r.mode === 'navigate') {
    /* r229：先抓網路（有改才下載，沒改只回 304），3 秒內沒回應或離線才用手機存的版本 */
    const key = u.origin + u.pathname + (u.pathname.endsWith('/') ? 'index.html' : '');
    e.respondWith(caches.open(P + 'core|' + V).then(c => c.match(key).then(m => {
      const net = fetch(new Request(u.origin + u.pathname + u.search, {cache: 'no-cache', credentials: 'same-origin'})).then(res => {
        if (res.ok && res.type === 'basic') c.put(key, res.clone()).catch(() => {});
        return res;
      });
      if (!m) return net.catch(() => caches.match('./index.html').then(x => x || caches.match('./')));
      e.waitUntil(net.catch(() => {}));
      const late = new Promise(ok => setTimeout(() => ok(null), 3000));
      return Promise.race([net.catch(() => null), late]).then(res => (res && res.ok) ? res : m.clone());
    })));
    return;
  }
  const same = u.origin === scope.origin;
  const font = /(^|\.)fonts\.(googleapis|gstatic)\.com$/.test(u.hostname);
  if (!same && !font) return;
  e.respondWith(caches.open(P + 'rt').then(c => c.match(r).then(m => {
    const f = fetch(r).then(res => { if (res.ok && res.type !== 'opaque') c.put(r, res.clone()); return res; }).catch(() => m);
    if (m) { e.waitUntil(f.catch(() => {})); return m; }
    return f;
  })));
});
