const CACHE = "checklist-chulucanas-v1";
const CORE = [
  "/",
  "/static/css/app.css",
  "/static/js/app.js",
  "/static/img/icon.svg",
  "/static/img/icons.svg",
];

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(CORE)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  if (event.request.method !== "GET" || url.pathname.startsWith("/api/")) {
    return;
  }

  if (url.origin === location.origin && (url.pathname === "/" || url.pathname.startsWith("/static/"))) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        const fetched = fetch(event.request)
          .then((response) => {
            if (response.ok) {
              const copy = response.clone();
              caches.open(CACHE).then((cache) => cache.put(event.request, copy));
            }
            return response;
          })
          .catch(() => cached);
        return cached || fetched;
      })
    );
  }
});