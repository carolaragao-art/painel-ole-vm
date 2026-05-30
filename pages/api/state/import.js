// Importa um bloco inteiro de estado (migração dos dados antigos do navegador).
//   POST { data: { chave: valor, ... }, force?: boolean }
import { importState } from '../../../lib/db';
import { getSession } from '../../../lib/auth';

export const config = { api: { bodyParser: { sizeLimit: '5mb' } } };

export default async function handler(req, res) {
  if (!getSession(req)) {
    res.status(401).json({ error: 'nao autenticado' });
    return;
  }
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    res.status(405).json({ error: 'metodo nao permitido' });
    return;
  }
  try {
    let body = req.body;
    if (typeof body === 'string') {
      try { body = JSON.parse(body); } catch (e) { body = {}; }
    }
    const data = (body && body.data) || {};
    const force = !!(body && body.force);
    const imported = await importState(data, force);
    res.status(200).json({ ok: true, imported });
  } catch (e) {
    console.error('Erro /api/state/import:', e.message);
    res.status(500).json({ error: 'erro interno' });
  }
}
