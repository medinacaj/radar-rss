/* Radar-RSS — lectura sin conexión.
   Estrategia: primero la red (siempre lo más reciente); si no hay conexión, la última
   copia guardada. Solo se guardan archivos del propio sitio, nunca imágenes ni enlaces externos.
   Las URL se guardan sin parámetros (?v=, ?check=) para que la caché no crezca sin límite. */
const CACHE = 'radar-rss-v73';
const SHELL = [
  './', './index.html', './manifest.webmanifest', './radar-rss-mark.png', './radar-rss-favicon-64.png', './radar-rss-social-card.png',
  './radar-rss-icon-192.png', './radar-rss-icon-512.png', './radar-rss-maskable-512.png', './radar-rss-apple-touch-icon.png',
  './styles.css', './dimension.css', './library.css',
  './sidebar-layout.css', './modal-layout.css', './news-effects.css', './sidebar-health.css', './ux.css', './features.css',
  './v12.css', './v13.css', './source-tools.js', './app.js', './v12.js', './v13.js', './library.js', './sidebar-layout.js', './news-effects.js', './features.js',
  './usability.css', './usability.js', './homepage.css', './homepage.js', './agenda.css', './agenda.js', './reader-layout.css', './reading-ux.css', './feed-ux.js', './reader-ux.js', './editorial-model.js', './editorial-ux.js', './editorial-ux.css', './experience.js', './experience.css',
  './data/latest.json', './data/sources.json', './data/status.json', './data/meta.json', './data/trends.json', './data/events.json',
];

const keyFor = request => {
  const url = new URL(request.url);
  return url.origin + url.pathname;
};

self.addEventListener('install', event => {
  // addAll es atómico: un fallo conserva activo el lector anterior y su caché.
  // Solo una copia completa puede pasar a activate y retirar las versiones viejas.
  event.waitUntil(caches.open(CACHE)
    .then(cache => cache.addAll(SHELL.map(path => new Request(path, { cache: 'reload' }))))
    .then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(key => (key.startsWith('radar-rss-') || key.startsWith('notisonda-')) && key !== CACHE).map(key => caches.delete(key))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  // Never cache range requests or requests outside the app's own scope.
  if (request.headers.has('range') || request.cache === 'only-if-cached' && request.mode !== 'same-origin') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin || !url.pathname.startsWith(new URL(self.registration.scope).pathname)) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    try {
      const response = await fetch(request);
      if (response.ok && response.type === 'basic' && !url.pathname.endsWith('/sw.js')) {
        event.waitUntil(cache.put(keyFor(request), response.clone()).catch(() => {}));
      }
      return response;
    } catch (error) {
      // Una comprobación manual exige red: una copia antigua no demuestra
      // que no haya novedades. El resto de la lectura sigue disponible offline.
      if (request.cache === 'no-store') throw error;
      const cached = await cache.match(keyFor(request));
      if (cached) return cached;
      if (request.mode === 'navigate') {
        const shell = await cache.match(keyFor(new Request('./index.html')));
        if (shell) return shell;
      }
      throw error;
    }
  })());
});
