// service-worker.js
// GI Intranet Offline-First Caching + PWA Support

const CACHE_NAME = "gi-intranet-cache-v1";
const OFFLINE_URL = "/offline.html";

// Files & routes to precache
const PRECACHE_ASSETS = [
  "/",                        // index.html (homepage)
  "/index.html",
  "/offline.html",            // fallback offline page
  "/styles/main.css",         // main stylesheet
  "/scripts/main.js",         // core client script
  "/sites/dev_vault.html",    // hidden programming & game dev vault
  "/icons/icon-192.png",      // PWA icons
  "/icons/icon-512.png"
];

// Install event: pre-cache important files
self.addEventListener("install", (event) => {
  console.log("[ServiceWorker] Install event triggered");
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log("[ServiceWorker] Precaching assets");
      return cache.addAll(PRECACHE_ASSETS);
    })
  );
  self.skipWaiting(); // Activate immediately after install
});

// Activate event: cleanup old caches
self.addEventListener("activate", (event) => {
  console.log("[ServiceWorker] Activate event triggered");
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((name) => {
          if (name !== CACHE_NAME) {
            console.log("[ServiceWorker] Deleting old cache:", name);
            return caches.delete(name);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch event: network-first with fallback to cache
self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return; // Only handle GET requests

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Clone and cache new response
        const resClone = response.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, resClone);
        });
        return response;
      })
      .catch(() => {
        // If offline, try cache first
        return caches.match(event.request).then((cachedRes) => {
          return cachedRes || caches.match(OFFLINE_URL);
        });
      })
  );
});
