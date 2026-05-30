/* ════════════════════════════════════════════════════════════════════
   PONTE DE DADOS — Olé VM
   Substitui o localStorage do painel por persistência no PostgreSQL,
   SEM alterar uma linha sequer do código original do painel.

   Como funciona:
   - O servidor injeta window.__OLE_STATE__ com o estado atual do banco.
   - Este script cria um "localStorage" sob medida:
       getItem  -> lê do cache (já vindo do banco), de forma síncrona
       setItem  -> grava no cache e envia ao banco (debounce)
       removeItem/clear -> idem
   - Na PRIMEIRA carga, se o banco estiver vazio mas o navegador tiver
     dados antigos no localStorage real, eles são migrados para o banco.
   ════════════════════════════════════════════════════════════════════ */
(function () {
  var KEYS = [
    'ole_ap_cellstate', 'ole_ap_projetos', 'ole_ff_fichas', 'ole_projetos',
    'ole_sp_epics', 'ole_sp_hist', 'ole_sp_meta', 'ole_sp_rec', 'ole_sp_sem',
    'ole_sp_tasks', 'ole_tasks', 'ole_updates'
  ];

  var server = window.__OLE_STATE__ || {};

  // Guarda referência ao localStorage REAL antes de substituí-lo (p/ migração).
  var realLS = null;
  try { realLS = window.localStorage; } catch (e) { realLS = null; }

  // Cache em memória — fonte síncrona de verdade durante a sessão.
  var cache = {};
  Object.keys(server).forEach(function (k) { cache[k] = server[k]; });

  // ── Migração automática: navegador antigo -> banco ──
  // Só roda quando o banco não tem NENHUM dado das chaves conhecidas,
  // mas o localStorage real do navegador tem.
  var serverHasData = KEYS.some(function (k) { return server[k] != null; });
  var pendingMigration = null;
  if (!serverHasData && realLS) {
    var fromBrowser = {};
    var anyBrowser = false;
    KEYS.forEach(function (k) {
      try {
        var v = realLS.getItem(k);
        if (v != null) { fromBrowser[k] = v; cache[k] = v; anyBrowser = true; }
      } catch (e) {}
    });
    if (anyBrowser) pendingMigration = fromBrowser;
  }

  // ── Fila de gravação (debounce por chave) ──
  var dirty = {};
  var timer = null;
  function flush() {
    timer = null;
    var keys = Object.keys(dirty);
    if (!keys.length) return;
    var batch = {};
    keys.forEach(function (k) { batch[k] = dirty[k]; });
    dirty = {};
    keys.forEach(function (k) {
      fetch('/api/state', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ key: k, value: batch[k] })
      }).catch(function () {
        // Em caso de falha, recoloca na fila para tentar de novo depois.
        dirty[k] = batch[k];
        schedule();
      });
    });
  }
  function schedule() {
    if (timer) return;
    timer = setTimeout(flush, 600);
  }
  function queueSave(k, v) { dirty[k] = v; schedule(); }

  // Flush garantido ao sair/ocultar a página.
  function flushBeacon() {
    var keys = Object.keys(dirty);
    if (!keys.length) return;
    keys.forEach(function (k) {
      try {
        var blob = new Blob([JSON.stringify({ key: k, value: dirty[k] })], { type: 'application/json' });
        navigator.sendBeacon('/api/state', blob);
      } catch (e) {}
    });
    dirty = {};
  }
  window.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') flushBeacon();
  });
  window.addEventListener('pagehide', flushBeacon);
  window.addEventListener('beforeunload', flushBeacon);

  // ── localStorage sob medida ──
  var shim = {
    getItem: function (k) { return Object.prototype.hasOwnProperty.call(cache, k) ? cache[k] : null; },
    setItem: function (k, v) { cache[k] = String(v); queueSave(k, cache[k]); },
    removeItem: function (k) { delete cache[k]; queueSave(k, null); },
    clear: function () { Object.keys(cache).forEach(function (k) { delete cache[k]; queueSave(k, null); }); },
    key: function (i) { return Object.keys(cache)[i] || null; }
  };
  Object.defineProperty(shim, 'length', { get: function () { return Object.keys(cache).length; } });

  try {
    Object.defineProperty(window, 'localStorage', { value: shim, configurable: true });
  } catch (e) {
    try { window.localStorage = shim; } catch (e2) {}
  }

  // Dispara a migração (se houver) — força=true só nesta primeira vez.
  if (pendingMigration) {
    fetch('/api/state/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ data: pendingMigration, force: true })
    }).then(function () {
      console.log('[Olé] Dados antigos do navegador migrados para o banco.');
    }).catch(function () {});
  }

  // ── Botão flutuante de logout + identificação do usuário ──
  window.addEventListener('DOMContentLoaded', function () {
    try {
      var bar = document.createElement('div');
      bar.style.cssText = 'position:fixed;bottom:14px;right:14px;z-index:9999;display:flex;align-items:center;gap:8px;background:#1D3461;color:#fff;padding:6px 10px;border-radius:20px;font-family:Poppins,sans-serif;font-size:12px;box-shadow:0 4px 16px rgba(0,0,0,.25)';
      var who = window.__OLE_USER__ ? ('👤 ' + window.__OLE_USER__) : '👤';
      bar.innerHTML = '<span>' + who + '</span>';
      var btn = document.createElement('button');
      btn.textContent = 'Sair';
      btn.style.cssText = 'background:#E8622A;color:#fff;border:none;border-radius:14px;padding:4px 12px;font:inherit;cursor:pointer;font-weight:600';
      btn.onclick = function () {
        fetch('/api/logout', { method: 'POST', credentials: 'same-origin' })
          .then(function () { window.location.href = '/login'; });
      };
      bar.appendChild(btn);
      document.body.appendChild(bar);
    } catch (e) {}
  });
})();
