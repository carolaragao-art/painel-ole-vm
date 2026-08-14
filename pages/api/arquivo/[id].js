// Visualização e remoção de um arquivo anexado.
//   GET    -> conteúdo inline (abre o PDF/imagem no navegador)
//   DELETE -> remove do banco
import { pool, ensureArquivos } from '../../../lib/db';
import { getSession } from '../../../lib/auth';

export default async function handler(req, res) {
  if (!getSession(req)) {
    res.status(401).json({ error: 'nao autenticado' });
    return;
  }
  const { id } = req.query;
  try {
    await ensureArquivos();
    if (req.method === 'GET') {
      const { rows } = await pool.query('SELECT nome, mime, dados FROM arquivos WHERE id = $1', [id]);
      if (!rows.length) {
        res.status(404).json({ error: 'arquivo nao encontrado' });
        return;
      }
      const a = rows[0];
      const buf = Buffer.from(a.dados, 'base64');
      res.setHeader('Content-Type', a.mime);
      res.setHeader('Content-Disposition', `inline; filename="${encodeURIComponent(a.nome)}"`);
      res.setHeader('Cache-Control', 'private, max-age=3600');
      res.status(200).send(buf);
      return;
    }
    if (req.method === 'DELETE') {
      await pool.query('DELETE FROM arquivos WHERE id = $1', [id]);
      res.status(200).json({ ok: true });
      return;
    }
    res.setHeader('Allow', 'GET, DELETE');
    res.status(405).json({ error: 'metodo nao permitido' });
  } catch (e) {
    console.error('Erro /api/arquivo/[id]:', e.message);
    res.status(500).json({ error: 'erro interno' });
  }
}
