const CACHE_NAME = 'gi-dev-vault-cache-v1';
const urlsToCache = [
  '/',
  '/index.html',
  '/dev_vault.html',
  // Add any CSS or JS files referenced by pages:
  // '/css/styles.css',
  // '/js/main.js',
  // Add local video files if you host videos locally, e.g.:
  // '/videos/python_tutorial.mp4',
];

// Install event - cache the app shell and content
self.addEventListener('install', event => {
  console.log('[ServiceWorker] Install');
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      console.log('[ServiceWorker] Caching app shell and content');
      return cache.addAll(urlsToCache);
    })
  );
});

// Activate event - cleanup old caches if any
self.addEventListener('activate', event => {
  console.log('[ServiceWorker] Activate');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('[ServiceWorker] Removing old cache', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Fetch event - serve cached content if offline, update cache when online
self.addEventListener('fetch', event => {
  // Only handle GET requests
  if (event.request.method !== 'GET') return;

  event.respondWith(
    caches.match(event.request).then(cachedResponse => {
      if (cachedResponse) {
        // Serve from cache
        return cachedResponse;
      }
      // Fetch from network, then cache the response for next time
      return fetch(event.request)
        .then(networkResponse => {
          // Check for valid response
          if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
            return networkResponse;
          }
          // Clone the response to cache it
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseToCache);
          });
          return networkResponse;
        })
        .catch(() => {
          // Offline fallback can be added here, e.g., offline.html
          return new Response('You are offline and the resource is not cached.');
        });
    })
  );
});
