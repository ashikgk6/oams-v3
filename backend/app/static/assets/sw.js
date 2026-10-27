self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open("oams-v2").then((cache) =>
      cache.addAll(["/", "/assets/styles.css", "/assets/app.js", "/assets/manifest.json"])
    )
  );
  self.skipWaiting();
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith("/api/")) return;
  e.respondWith(
    caches.match(e.request).then((cached) => cached || fetch(e.request))
  );
});
