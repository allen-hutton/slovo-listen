// Rashody service worker: keeps the app itself available offline.
// Data never goes through here — entries live in the page's storage and sync to GitHub directly.
const CACHE = "rashody-v10";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icon-180.png", "icon-192.png", "icon-512.png",
  "vendor/leaflet.js", "vendor/leaflet.css", "vendor/pmtiles.js", "vendor/protomaps-leaflet.js"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;   // GitHub API calls go straight to the network
  if (url.pathname.endsWith(".pmtiles") || url.pathname.endsWith(".bin")) return;     // the map file is kept in the page's own storage, not twice
  // network first (so updates arrive), cached copy when offline
  e.respondWith(
    fetch(e.request).then(r => {
      if (r.ok) { const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); }
      return r;
    }).catch(() => caches.match(e.request, { ignoreSearch: true }).then(r => r || caches.match("index.html")))
  );
});
