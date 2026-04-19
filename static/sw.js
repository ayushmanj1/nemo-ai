const CACHE_NAME = 'thing-ai-v1.1.2';
const ASSETS_TO_CACHE = [
  '/',
  '/manifest.json',
  '/static/icon-192.png',
  '/static/icon-512.png',
  'https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700&family=DM+Sans:wght@300;400;500&display=swap'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.filter((name) => name !== CACHE_NAME).map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);
  
  // Network-First strategy for the root page to ensure updates are seen immediately
  if (url.pathname === '/') {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const clonedResponse = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clonedResponse));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // Cache-First for static assets defined in ASSETS_TO_CACHE
  if (ASSETS_TO_CACHE.includes(url.pathname)) {
    event.respondWith(
      caches.match(event.request).then((cachedResponse) => {
        return cachedResponse || fetch(event.request);
      })
    );
  } else {
    // Network-only (with cache fallback) for everything else
    event.respondWith(
      fetch(event.request).catch(() => {
        return caches.match(event.request);
      })
    );
  }
});
