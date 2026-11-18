// Serve marcos.html e projetos.html — sempre a cópia MAIS NOVA.
//
// Existem duas rotinas que geram essas páginas:
//   1. o notebook da Carol (tarefa horária) -> commit no repo -> arquivo em public/
//   2. o servidor (/api/importar, chamado pelo Apps Script) -> tabela rotina_painel
//
// A versão anterior desta rota preferia sempre o banco. Como a etapa 2 ficou
// pela metade (falta uma autorização do Google), o banco congelou em 29/10 e a
// aba Marcos & Metas passou 20 dias mostrando dado velho, mesmo com a rotina 1
// publicando todo dia. Agora a rota compara as duas datas e entrega a mais
// recente — funciona com qualquer uma das rotinas viva, ou com as duas.
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

  // ── candidata 1: banco
  let doBanco = null;
  try {
    await ensureSchema();
    const r = await pool.query(
      'SELECT v, updated_at FROM rotina_painel WHERE k = $1', [alvo.chave]);
    if (r.rows.length && r.rows[0].v) {
      doBanco = { html: r.rows[0].v, em: new Date(r.rows[0].updated_at || 0) };
    }
  } catch (e) {
    console.error('pagina: falha ao ler do banco —', e.message);
  }

  // ── candidata 2: arquivo publicado pelo repositório
  let doArquivo = null;
  try {
    const caminho = path.join(process.cwd(), 'public', alvo.arquivo);
    doArquivo = { html: fs.readFileSync(caminho, 'utf8'), em: fs.statSync(caminho).mtime };
  } catch (e) {
    console.error('pagina: falha ao ler o arquivo —', e.message);
  }

  if (!doBanco && !doArquivo) {
    res.status(500).send('pagina indisponivel');
    return;
  }

  let escolhida, origem;
  if (doBanco && doArquivo) {
    const bancoMaisNovo = doBanco.em >= doArquivo.em;
    escolhida = bancoMaisNovo ? doBanco : doArquivo;
    origem = bancoMaisNovo ? 'banco' : 'arquivo';
  } else {
    escolhida = doBanco || doArquivo;
    origem = doBanco ? 'banco' : 'arquivo';
  }

  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store, must-revalidate');
  res.setHeader('X-Ole-Origem', origem);
  res.setHeader('X-Ole-Gerado', escolhida.em.toISOString());
  res.status(200).send(escolhida.html);
}
