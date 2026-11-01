/* Brew Calculator service worker: offline app shell.
   CACHE_VERSION is stamped automatically from the app's files by tools/stamp-version.py; run it before each upload
   so installed copies notice the change. Editing the number by hand also works. */
const CACHE_VERSION = 'c0c5b66a4e9';
const CACHE = `brew-calculator-${CACHE_VERSION}`;
const SHELL = ['./', './index.html', './manifest.webmanifest', './icons/icon-192.png', './icons/icon-512.png', './icons/maskable-512.png', './icons/apple-touch-icon.png'];

self.addEventListener('install', (event) => {
  // cache: 'reload' skips the host's HTTP cache, so a new version never precaches stale copies of its own files
  event.waitUntil(caches.open(CACHE).then((c) => Promise.all(SHELL.map((u) => c.add(new Request(u, { cache: 'reload' }))))));   // no skipWaiting: the page offers the update, and the person decides when
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith('brew-calculator-') && k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== self.location.origin) return;
  if (req.mode === 'navigate') {   // network first so a new version is picked up; cached copy when offline
    event.respondWith(
      fetch(req, { cache: 'no-cache' }).then((res) => { if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put('./index.html', copy)); } return res; })
        .catch(() => caches.match('./index.html').then((hit) => hit || caches.match('./')))
    );
    return;
  }
  event.respondWith(   // everything else: cache first, fill the cache on a miss
    caches.match(req).then((hit) => hit || fetch(req).then((res) => {
      if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(req, copy)); }
      return res;
    }))
  );
});

/* Tapping a timer notification brings the app back to the front. */
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
    const open = list.find((c) => 'focus' in c);
    return open ? open.focus() : self.clients.openWindow('./#timer');
  }));
});

/* The page asks for activation once the person taps "Update now". */
self.addEventListener('message', (event) => {
  if (event.data === 'SKIP_WAITING') self.skipWaiting();
  else if (event.data === 'VERSION' && event.ports[0]) event.ports[0].postMessage({ version: CACHE_VERSION });   // lets the Settings page show which version is running
});
