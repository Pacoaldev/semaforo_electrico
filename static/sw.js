/* Semáforo Eléctrico - Service Worker (PWA)
 *
 * Estrategia:
 *  - Precachea el "app shell" (manifest + iconos) al instalar.
 *  - Navegación (HTML): network-first con fallback a caché (para ver algo offline).
 *  - API / datos: network-first, sin cachear respuestas de precios (siempre frescos).
 *  - Estáticos (CSS/JS/imágenes): stale-while-revalidate (sirve rápido y
 *    actualiza en segundo plano, para no quedarse con versiones viejas).
 */

const CACHE_VERSION = 'semaforo-v2';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const PAGES_CACHE = `${CACHE_VERSION}-pages`;

const PRECACHE_URLS = [
  '/static/manifest.json',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

// Instalación: precachea el app shell.
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
});

// Activación: limpia cachés antiguas.
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => !key.startsWith(CACHE_VERSION))
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// Mensaje desde la página: forzar activación inmediata de una versión nueva.
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Solo gestionamos GET.
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // No interferir con peticiones a otros orígenes (CDN de Tailwind, fuentes...).
  if (url.origin !== self.location.origin) return;

  // Peticiones de navegación (documentos HTML): network-first.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(PAGES_CACHE).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Archivos estáticos: stale-while-revalidate.
  // Se sirve la copia en caché (rápido) y, en paralelo, se pide a la red para
  // actualizar la caché de cara a la próxima visita. Evita quedarse "pegado"
  // a versiones antiguas de CSS/JS.
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.open(STATIC_CACHE).then((cache) =>
        cache.match(request).then((cached) => {
          const networkFetch = fetch(request)
            .then((response) => {
              cache.put(request, response.clone());
              return response;
            })
            .catch(() => cached);
          return cached || networkFetch;
        })
      )
    );
    return;
  }

  // Resto (API, etc.): network-first sin cachear (siempre datos frescos).
  event.respondWith(fetch(request).catch(() => caches.match(request)));
});
