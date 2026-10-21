/* Service worker – Revision Desk (offline-first)
 * Đặt sw.js cùng thư mục với file HTML. Đổi VERSION mỗi khi bạn cập nhật HTML để ép làm mới cache. */
const VERSION = 'v2';
const CACHE = 'revision-desk-' + VERSION;
const FONT_CACHE = 'revision-desk-fonts';
const PRECACHE = ['./', 'favicon.png'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) =>
      // addAll fail nếu 1 file lỗi -> thêm từng file, bỏ qua file thiếu (vd. favicon.png)
      Promise.all(PRECACHE.map((u) => cache.add(u).catch(() => null)))
    ).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => k.startsWith('revision-desk-') && k !== CACHE && k !== FONT_CACHE)
            .map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

// Trang gửi URL của chính nó để cache ngay lần đầu (dù file HTML tên gì)
self.addEventListener('message', (event) => {
  if (!event.data || event.data.type !== 'CACHE_URLS') return;
  event.waitUntil(
    caches.open(CACHE).then((cache) =>
      Promise.all(event.data.urls.map((u) => cache.add(u).catch(() => null)))
    )
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // Google Fonts & CDN: stale-while-revalidate (cache cả phản hồi opaque)
  if (url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com' || url.hostname === 'cdn.jsdelivr.net') {
    event.respondWith(
      caches.open(FONT_CACHE).then((cache) =>
        cache.match(req).then((cached) => {
          const network = fetch(req).then((res) => {
            if (res && (res.ok || res.type === 'opaque')) cache.put(req, res.clone());
            return res;
          }).catch(() => cached);
          return cached || network;
        })
      )
    );
    return;
  }

  // Chỉ xử lý cùng origin; link ngoài (chatgpt, claude, gemini) để trình duyệt tự xử lý
  if (url.origin !== self.location.origin) return;

  // Điều hướng trang: network-first, rớt mạng thì dùng bản cache
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req).then((res) => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      }).catch(() =>
        caches.match(req, { ignoreSearch: true })
          .then((r) => r || caches.match('./'))
          .then((r) => r || caches.match(self.registration.scope + 'index.html'))
      )
    );
    return;
  }

  // Tài nguyên khác cùng origin: stale-while-revalidate
  event.respondWith(
    caches.open(CACHE).then((cache) =>
      cache.match(req, { ignoreSearch: true }).then((cached) => {
        const network = fetch(req).then((res) => {
          if (res && res.ok) cache.put(req, res.clone());
          return res;
        }).catch(() => cached);
        return cached || network;
      })
    )
  );
});
