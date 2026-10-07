/* Iris Nous companion PWA — cache shell only (API always network). */
const CACHE = "iris-app-v3-glass";
const SHELL = [
  "/app",
  "/static/app/app.css?v=irisGlass3",
  "/static/app/app.js?v=irisGlass3",
  "/static/app/manifest.webmanifest",
  "/static/app/icon-180.png",
  "/static/app/icon-192.png",
  "/static/app/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.pathname.startsWith("/api/")) return;
  event.respondWith(
    caches.match(req).then((cached) => {
      const net = fetch(req)
        .then((res) => {
          if (res.ok && (url.pathname.startsWith("/static/app/") || url.pathname === "/app")) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy));
          }
          return res;
        })
        .catch(() => cached);
      return cached || net;
    })
  );
});
