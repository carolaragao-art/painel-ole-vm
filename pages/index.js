// Serve o painel HTML original no servidor (rota raiz "/"), com:
//  - checagem de login (redireciona para /login)
//  - injeção do estado vindo do PostgreSQL (__OLE_STATE__) e do usuário
//  - inclusão do script ponte /ole-bridge.js
import fs from 'fs';
import path from 'path';
import { getAllState } from '../lib/db';
import { getSession } from '../lib/auth';

let cachedHtml = null;
function loadHtml() {
  if (cachedHtml) return cachedHtml;
  const candidates = [
    path.join(process.cwd(), 'public', 'painel.html'),
    path.join(process.cwd(), 'painel.html'),
  ];
  for (const f of candidates) {
    try { cachedHtml = fs.readFileSync(f, 'utf8'); return cachedHtml; } catch (e) {}
  }
  throw new Error('painel.html nao encontrado');
}

export async function getServerSideProps(ctx) {
  const { req, res } = ctx;
  const session = getSession(req);
  if (!session) {
    return { redirect: { destination: '/login', permanent: false } };
  }

  let state = {};
  try { state = await getAllState(); } catch (e) { console.error('estado:', e.message); }

  let html;
  try { html = loadHtml(); }
  catch (e) {
    res.statusCode = 500;
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.end('<h1>Erro ao carregar o painel</h1><p>' + e.message + '</p>');
    return { props: {} };
  }

  const inject =
    '\n<script>window.__OLE_STATE__=' + JSON.stringify(state) +
    ';window.__OLE_USER__=' + JSON.stringify(session.user || '') + ';</script>' +
    '\n<script src="/ole-bridge.js"></script>\n';

  const out = /<head[^>]*>/i.test(html)
    ? html.replace(/<head[^>]*>/i, (m) => m + inject)
    : inject + html;

  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.write(out);
  res.end();
  return { props: {} };
}

export default function Index() { return null; }
