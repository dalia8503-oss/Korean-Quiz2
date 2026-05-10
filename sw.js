const CACHE = 'kq-v29';

// 설치: 캐시 작업 없이 즉시 완료 → 404로 실패할 일 없음
self.addEventListener('install', e => {
  e.waitUntil(self.skipWaiting());
});

// 활성화: 모든 구버전 캐시 삭제 → 클라이언트 인계 → 페이지 자동 새로고침
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.map(k => caches.delete(k))))
      .then(() => self.clients.claim())
      .then(() => self.clients.matchAll({ type: 'window', includeUncontrolled: true }))
      .then(clients => Promise.all(clients.map(c => c.navigate(c.url))))
  );
});

// fetch: HTML은 항상 네트워크에서 (캐시 없이 최신 버전)
self.addEventListener('fetch', e => {
  if (e.request.mode === 'navigate') {
    e.respondWith(fetch(e.request));
    return;
  }
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request))
  );
});
