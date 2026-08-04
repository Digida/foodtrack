const CACHE = 'foodtrack-v3';
const PRECACHE = [
  '/',
  '/index.html',
  '/sso.html',
  '/css/app.css',
  '/js/api.js',
  '/js/auth.js',
  '/js/seo.js',
  '/js/router.js',
  '/js/components.js',
  '/js/pages.js',
  '/js/app.js',
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
  );
});

self.addEventListener('fetch', (e) => {
  if (!e.request.url.startsWith(self.location.origin) || e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request).then((res) => {
      if (res.ok && res.type === 'basic') {
        const clone = res.clone();
        caches.open(CACHE).then((cache) => cache.put(e.request, clone));
      }
      return res;
    }).catch(() => caches.match(e.request))
  );
});
