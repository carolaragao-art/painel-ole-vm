// Verificação leve de versão do estado (para sincronização automática).
// Retorna { version } — uma string que muda sempre que algo é salvo.
import { getStateVersion } from '../../../lib/db';
import { getSession } from '../../../lib/auth';

export default async function handler(req, res) {
  if (!getSession(req)) {
    res.status(401).json({ error: 'nao autenticado' });
    return;
  }
  try {
    const v = await getStateVersion();
    res.setHeader('Cache-Control', 'no-store');
    res.status(200).json(v);
  } catch (e) {
    console.error('Erro /api/state/version:', e.message);
    res.status(500).json({ error: 'erro interno' });
  }
}
