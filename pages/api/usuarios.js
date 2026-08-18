// Administração de logins do painel (somente administradora).
//   GET  -> { ok, usuarios: [nomes] }
//   POST { op:'add'|'reset', usuario, senha } | { op:'remove', usuario }
import { pool } from '../../lib/db';
import { getSession, hashSenha, ensureAuthUsers, seedFromEnvIfEmpty } from '../../lib/auth';

const ADMINS = ['carol'];

export default async function handler(req, res) {
  const sess = getSession(req);
  if (!sess) {
    res.status(401).json({ error: 'nao autenticado' });
    return;
  }
  if (ADMINS.indexOf(sess.user) === -1) {
    res.status(403).json({ error: 'somente a administradora pode gerenciar logins' });
    return;
  }
  try {
    await ensureAuthUsers();
    await seedFromEnvIfEmpty();

    if (req.method === 'GET') {
      const { rows } = await pool.query('SELECT usuario FROM auth_users ORDER BY usuario');
      res.status(200).json({ ok: true, usuarios: rows.map((r) => r.usuario) });
      return;
    }

    if (req.method === 'POST') {
      let body = req.body;
      if (typeof body === 'string') {
        try { body = JSON.parse(body); } catch (e) { body = {}; }
      }
      const op = (body && body.op) || '';
      const usuario = String((body && body.usuario) || '').trim().toLowerCase();
      if (!usuario || !/^[a-z0-9._-]{2,30}$/.test(usuario)) {
        res.status(400).json({ error: 'usuario invalido (use letras minusculas, numeros, ponto ou hifen)' });
        return;
      }

      if (op === 'add' || op === 'reset') {
        const senha = String((body && body.senha) || '');
        if (senha.length < 4) {
          res.status(400).json({ error: 'senha muito curta (minimo 4 caracteres)' });
          return;
        }
        await pool.query(
          'INSERT INTO auth_users (usuario, hash) VALUES ($1, $2) ON CONFLICT (usuario) DO UPDATE SET hash = EXCLUDED.hash',
          [usuario, hashSenha(usuario, senha)]
        );
        res.status(200).json({ ok: true });
        return;
      }

      if (op === 'remove') {
        if (usuario === sess.user || ADMINS.indexOf(usuario) !== -1) {
          res.status(400).json({ error: 'nao e possivel remover a administradora' });
          return;
        }
        await pool.query('DELETE FROM auth_users WHERE usuario = $1', [usuario]);
        res.status(200).json({ ok: true });
        return;
      }

      res.status(400).json({ error: 'operacao invalida' });
      return;
    }

    res.setHeader('Allow', 'GET, POST');
    res.status(405).json({ error: 'metodo nao permitido' });
  } catch (e) {
    console.error('Erro /api/usuarios:', e.message);
    res.status(500).json({ error: 'erro interno' });
  }
}
