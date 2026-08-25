self.addEventListener('install', function(e) {
  self.skipWaiting();
});

self.addEventListener('fetch', function(event) {
  // Passa as requisições de rede normalmente mantendo a sessão Django ativa
});