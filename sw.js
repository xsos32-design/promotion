/* 離線模式：頁面走「網路優先、斷線用快取」，圖片字型走「快取優先、背景更新」 */
const V = 'v2026-10-10';
const P = self.registration.scope + '|';
const CORE = ['./', './index.html', './img/brand/hero.webp', './icon-192.png'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(P + 'core|' + V).then(c => c.addAll(CORE)).catch(() => {}).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith(P) && !k.endsWith(V)).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const r = e.request;
  if (r.method !== 'GET') return;
  const u = new URL(r.url);
  const scope = new URL(self.registration.scope);
  if (r.mode === 'navigate') {
    e.respondWith(fetch(r).then(res => {
      if (res.ok) { const cp = res.clone(); caches.open(P + 'core|' + V).then(c => c.put('./index.html', cp)); }
      return res;
    }).catch(() => caches.match('./index.html', {ignoreSearch: true}).then(m => m || caches.match('./'))));
    return;
  }
  const same = u.origin === scope.origin;
  const font = /(^|\.)fonts\.(googleapis|gstatic)\.com$/.test(u.hostname);
  if (!same && !font) return;
  e.respondWith(caches.open(P + 'rt|' + V).then(c => c.match(r).then(m => {
    const f = fetch(r).then(res => { if (res.ok && res.type !== 'opaque') c.put(r, res.clone()); return res; }).catch(() => m);
    return m || f;
  })));
});
