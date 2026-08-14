// Upload de arquivos (certidões e licenças).
//   POST { nome, mime, base64 } -> { ok, id }
import { pool, ensureArquivos } from '../../../lib/db';
import { getSession } from '../../../lib/auth';

export const config = { api: { bodyParser: { sizeLimit: '6mb' } } };

export default async function handler(req, res) {
  if (!getSession(req)) {
    res.status(401).json({ error: 'nao autenticado' });
    return;
  }
  try {
    if (req.method === 'POST') {
      let body = req.body;
      if (typeof body === 'string') {
        try { body = JSON.parse(body); } catch (e) { body = {}; }
      }
      const { nome, mime, base64 } = body || {};
      if (!nome || !base64 || typeof base64 !== 'string') {
        res.status(400).json({ error: 'nome e base64 obrigatorios' });
        return;
      }
      const tamanho = Math.floor(base64.length * 3 / 4);
      if (tamanho > 4.5 * 1024 * 1024) {
        res.status(413).json({ error: 'arquivo maior que 4MB' });
        return;
      }
      await ensureArquivos();
      const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
      await pool.query(
        'INSERT INTO arquivos (id, nome, mime, dados, tamanho) VALUES ($1, $2, $3, $4, $5)',
        [id, String(nome).slice(0, 200), mime || 'application/octet-stream', base64, tamanho]
      );
      res.status(200).json({ ok: true, id });
      return;
    }
    res.setHeader('Allow', 'POST');
    res.status(405).json({ error: 'metodo nao permitido' });
  } catch (e) {
    console.error('Erro /api/arquivo:', e.message);
    res.status(500).json({ error: 'erro interno' });
  }
}
