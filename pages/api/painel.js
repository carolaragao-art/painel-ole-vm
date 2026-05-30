// Serve o painel HTML ORIGINAL (intacto) + injeta:
//   1) window.__OLE_STATE__  com o estado atual vindo do PostgreSQL
//   2) o script ponte /ole-bridge.js que substitui o localStorage pelo banco
import fs from 'fs';
import path from 'path';
import { getAllState } from '../../lib/db';
import { getSession } from '../../lib/auth';

let cachedHtml = null;
function loadHtml() {
  if (cachedHtml) return cachedHtml;
  const file = path.join(process.cwd(), 'public', 'painel.html');
  cachedHtml = fs.readFileSync(file, 'utf8');
  return cachedHtml;
}

export default async function handler(req, res) {
  const session = getSession(req);
  if (!session) {
    res.writeHead(302, { Location: '/login' });
    res.end();
    return;
  }

  let state = {};
  try {
    state = await getAllState();
  } catch (e) {
    // Se o banco falhar, ainda servimos o painel (ele usa os defaults embutidos)
    console.error('Erro lendo estado:', e.message);
  }

  const html = loadHtml();

  const inject =
    `\n<script>window.__OLE_STATE__ = ${JSON.stringify(state)};` +
    `window.__OLE_USER__ = ${JSON.stringify(session.user || '')};</script>` +
    `\n<script src="/ole-bridge.js"></script>\n`;

  // Injeta logo após a abertura do <head> para rodar ANTES do script do painel.
  let out;
  if (/<head[^>]*>/i.test(html)) {
    out = html.replace(/<head[^>]*>/i, (m) => m + inject);
  } else {
    out = inject + html;
  }

  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.status(200).send(out);
}
