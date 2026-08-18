import { checkCredentialsAsync, makeToken, buildCookie } from '../../lib/auth';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    res.status(405).json({ error: 'metodo nao permitido' });
    return;
  }
  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) { body = {}; }
  }
  const { user, pass } = body || {};
  const ok = await checkCredentialsAsync(user, pass);
  if (!ok) {
    res.status(401).json({ error: 'Usuário ou senha inválidos' });
    return;
  }
  const token = makeToken(String(user).trim().toLowerCase());
  res.setHeader('Set-Cookie', buildCookie(token));
  res.status(200).json({ ok: true });
}
