/**
 * Atomadic Forge — service worker.
 *
 * App-shell offline strategy:
 *   - Static assets: stale-while-revalidate
 *   - Navigations:   network-first, fall back to cached "/" shell
 *   - /api/*:        network-only (forge CLI must be reachable)
 *
 * Cache name is keyed to the build version so a new deploy invalidates clients.
 */

const VERSION = "forge-web-v0.3.2";
const SHELL_CACHE = `${VERSION}-shell`;
const ASSET_CACHE = `${VERSION}-assets`;
const SHELL_URLS = ["/", "/manifest.webmanifest"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((c) => c.addAll(SHELL_URLS)).then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => !k.startsWith(VERSION))
          .map((k) => caches.delete(k)),
      ),
    ).then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  // Never cache forge backend
  if (url.pathname.startsWith("/api/")) return;

  // Navigations → network-first, fallback to shell
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req).catch(() => caches.match("/").then((r) => r ?? Response.error())),
    );
    return;
  }

  // Static assets → stale-while-revalidate
  if (url.origin === self.location.origin) {
    event.respondWith(
      caches.open(ASSET_CACHE).then(async (cache) => {
        const cached = await cache.match(req);
        const network = fetch(req)
          .then((res) => {
            if (res.ok) cache.put(req, res.clone());
            return res;
          })
          .catch(() => cached);
        return cached || network;
      }),
    );
  }
});
