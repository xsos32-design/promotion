/* r56：頁面先開手機存好的版本、背景只在有變時更新；圖片字型快取跨版本保留 */
const V = 'v2026-10-15-r135';
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
    const key = u.origin + u.pathname + (u.pathname.endsWith('/') ? 'index.html' : '');
    const net = fetch(new Request(u.origin + u.pathname + u.search, {cache: 'no-cache', credentials: 'same-origin'})).then(res => {
      if (res.ok) { const cp = res.clone(); caches.open(P + 'core|' + V).then(c => c.put(key, cp)); }
      return res;
    });
    e.waitUntil(net.catch(() => {}));
    e.respondWith(caches.match(key).then(m => {
      if (!m) return net.catch(() => caches.match('./index.html').then(x => x || caches.match('./')));
      const late = new Promise(ok => setTimeout(() => ok(m), 1200));
      return Promise.race([net.then(res => res.ok ? res : m).catch(() => m), late]);
    }));
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
