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
    'ole_sp_tasks', 'ole_tasks', 'ole_updates', 'ole_pipeline_cells',
    'ole_sp_num', 'ole_sp_week'
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

  // Chaves PURAMENTE LOCAIS deste navegador (não vão para o banco nem são
  // compartilhadas entre usuários). Ex.: a última aba aberta é preferência de cada um.
  var LOCAL_ONLY = { 'ole_ultima_aba': 1 };
  var realLSget = function (k) { try { return realLS ? realLS.getItem(k) : null; } catch (e) { return null; } };
  var realLSset = function (k, v) { try { if (realLS) realLS.setItem(k, v); } catch (e) {} };
  var realLSdel = function (k) { try { if (realLS) realLS.removeItem(k); } catch (e) {} };

  // ── localStorage sob medida ──
  var shim = {
    getItem: function (k) {
      if (LOCAL_ONLY[k]) return realLSget(k);
      return Object.prototype.hasOwnProperty.call(cache, k) ? cache[k] : null;
    },
    setItem: function (k, v) {
      if (LOCAL_ONLY[k]) { realLSset(k, String(v)); return; }
      cache[k] = String(v); queueSave(k, cache[k]);
    },
    removeItem: function (k) {
      if (LOCAL_ONLY[k]) { realLSdel(k); return; }
      delete cache[k]; queueSave(k, null);
    },
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

  // ════════════════════════════════════════════════════════════
  // SINCRONIZAÇÃO AUTOMÁTICA (a cada 15s)
  // - Verifica de forma leve se alguém alterou os dados no banco.
  // - Atualiza a tela sozinho QUANDO é seguro (ninguém digitando).
  // - Se você estiver editando, mostra um botão discreto "Atualizar".
  // ════════════════════════════════════════════════════════════
  var POLL_MS = 15000;
  var knownVersion = null;
  var reloadBanner = null;

  function fetchVersion() {
    return fetch('/api/state/version', { credentials: 'same-origin', cache: 'no-store' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) { return j ? j.version : null; })
      .catch(function () { return null; });
  }

  // Estabelece a versão base ao abrir a página.
  fetchVersion().then(function (v) { knownVersion = v; });

  // Após cada gravação nossa, atualiza a versão base (evita auto-recarregar
  // por causa da própria edição).
  var origFlush = flush;
  flush = function () {
    origFlush();
    setTimeout(function () { fetchVersion().then(function (v) { if (v) knownVersion = v; }); }, 1200);
  };

  // Detecta se o usuário está no meio de uma edição (não interromper).
  function estaEditando() {
    var el = document.activeElement;
    if (el) {
      var tag = (el.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select' || el.isContentEditable) return true;
    }
    // Algum modal aberto?
    var modais = document.querySelectorAll('.modal-overlay, #bl-edit-item-modal, #apModal, #ffModal');
    for (var i = 0; i < modais.length; i++) {
      var m = modais[i];
      if (m && m.style && m.style.display !== 'none' && m.offsetParent !== null) return true;
    }
    // Há gravações pendentes nossas?
    if (Object.keys(dirty).length > 0) return true;
    return false;
  }

  function mostrarBannerAtualizar() {
    if (reloadBanner) return;
    reloadBanner = document.createElement('div');
    reloadBanner.style.cssText = 'position:fixed;bottom:58px;right:14px;z-index:10000;display:flex;align-items:center;gap:10px;background:#E8A020;color:#1D3461;padding:9px 14px;border-radius:12px;font-family:Poppins,sans-serif;font-size:12.5px;font-weight:600;box-shadow:0 6px 20px rgba(0,0,0,.28)';
    reloadBanner.innerHTML = '<span>🔄 Novos dados da equipe</span>';
    var b = document.createElement('button');
    b.textContent = 'Atualizar';
    b.style.cssText = 'background:#1D3461;color:#fff;border:none;border-radius:9px;padding:5px 12px;font:inherit;font-weight:700;cursor:pointer';
    b.onclick = function () { window.location.reload(); };
    reloadBanner.appendChild(b);
    document.body.appendChild(reloadBanner);
  }

  function checarAtualizacoes() {
    if (document.visibilityState === 'hidden') return; // não gasta em aba oculta
    fetchVersion().then(function (v) {
      if (!v || knownVersion === null) { if (v) knownVersion = v; return; }
      if (v === knownVersion) return;          // nada mudou
      // Mudou no banco (outra pessoa editou)
      if (estaEditando()) {
        mostrarBannerAtualizar();              // não interrompe: oferece o botão
      } else {
        window.location.reload();              // seguro: atualiza sozinho
      }
    });
  }

  setInterval(checarAtualizacoes, POLL_MS);
  // Verifica também ao voltar o foco para a aba.
  window.addEventListener('focus', checarAtualizacoes);
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible') checarAtualizacoes();
  });
})();
