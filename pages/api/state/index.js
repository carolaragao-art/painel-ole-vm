// API de estado compartilhado (todas as chaves ole_*).
//   GET  -> retorna { key: value, ... }
//   POST -> grava { key, value }  (value null remove)
import { getAllState, setState } from '../../../lib/db';
import { getSession } from '../../../lib/auth';

export default async function handler(req, res) {
  if (!getSession(req)) {
    res.status(401).json({ error: 'nao autenticado' });
    return;
  }

  try {
    if (req.method === 'GET') {
      const state = await getAllState();
      res.status(200).json(state);
      return;
    }

    if (req.method === 'POST') {
      let body = req.body;
      if (typeof body === 'string') {
        try { body = JSON.parse(body); } catch (e) { body = {}; }
      }
      const { key, value } = body || {};
      if (!key || typeof key !== 'string') {
        res.status(400).json({ error: 'key obrigatoria' });
        return;
      }
      await setState(key, value === undefined ? null : value);
      res.status(200).json({ ok: true });
      return;
    }

    res.setHeader('Allow', 'GET, POST');
    res.status(405).json({ error: 'metodo nao permitido' });
  } catch (e) {
    console.error('Erro /api/state:', e.message);
    res.status(500).json({ error: 'erro interno' });
  }
}
