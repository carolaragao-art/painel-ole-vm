// Serve marcos.html e projetos.html a partir do banco.
//
// Quem grava é /api/importar (função Python), logo depois que o Smartsheet manda
// o Excel por e-mail. Se o banco ainda não tiver a página — primeira vez, ou algum
// problema na importação — cai para o arquivo estático em public/, que continua
// sendo publicado pela rotina antiga. Assim a tela nunca fica em branco.
const fs = require('fs');
const path = require('path');
const { pool, ensureSchema } = require('../../lib/db');

const MAPA = {
  marcos: { chave: 'pagina_marcos', arquivo: 'marcos.html' },
  projetos: { chave: 'pagina_projetos', arquivo: 'projetos.html' },
};

export default async function handler(req, res) {
  const alvo = MAPA[String(req.query.nome || '')];
  if (!alvo) {
    res.status(404).send('pagina desconhecida');
    return;
  }

  let html = null;
  let origem = 'banco';
  try {
    await ensureSchema();
    const r = await pool.query('SELECT v FROM kv_state WHERE k = $1', [alvo.chave]);
    if (r.rows.length && r.rows[0].v) html = r.rows[0].v;
  } catch (e) {
    console.error('pagina: falha ao ler do banco', e.message);
  }

  if (!html) {
    try {
      html = fs.readFileSync(path.join(process.cwd(), 'public', alvo.arquivo), 'utf8');
      origem = 'arquivo';
    } catch (e) {
      res.status(500).send('pagina indisponivel');
      return;
    }
  }

  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store, must-revalidate');
  res.setHeader('X-Ole-Origem', origem);
  res.status(200).send(html);
}
