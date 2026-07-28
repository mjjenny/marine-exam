/* Engine Room Academy — basic cache-first service worker */
const CACHE_NAME = "era-static-v1";
const OFFLINE_URL = "/offline.html";
const PRECACHE_URLS = ["/", "/offline.html", "/manifest.json"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

function isStaticAsset(url) {
  return (
    url.pathname.startsWith("/assets/") ||
    /\.(?:js|css|png|jpg|jpeg|gif|svg|webp|woff2?|ttf|ico|json)$/i.test(url.pathname)
  );
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // Never intercept API, health, or the worker script itself.
  if (
    url.pathname.startsWith("/api/") ||
    url.pathname === "/health" ||
    url.pathname === "/sw.js"
  ) {
    return;
  }

  // Cache-first for hashed build assets and other static files.
  if (isStaticAsset(url)) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request)
          .then((response) => {
            if (response && response.ok) {
              const copy = response.clone();
              caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
            }
            return response;
          })
          .catch(() => cached);
      })
    );
    return;
  }

  // Navigations: try network, fall back to offline page (then cached shell).
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response && response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          }
          return response;
        })
        .catch(() =>
          caches.match(OFFLINE_URL).then((offline) => offline || caches.match("/"))
        )
    );
  }
});
