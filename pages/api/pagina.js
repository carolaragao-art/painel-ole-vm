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

// A data tem que sair de DENTRO da página: na Vercel o mtime dos arquivos é o
// do build, não o da geração, e isso fazia a cópia velha do banco ganhar.
function dataDaPagina(html) {
  if (!html) return null;
  let m = html.match(/<!--gerado_em:([^>]+?)-->/);              // projetos
  if (m) { const d = new Date(m[1]); if (!isNaN(d)) return d; }
  m = html.match(/"gerado_em":\s*"([^"]+)"/);                    // marcos
  if (m) { const d = new Date(m[1]); if (!isNaN(d)) return d; }
  m = html.match(/Smartsheet de <b>(\d{2})\/(\d{2})\/(\d{4})/);  // último recurso
  if (m) return new Date(+m[3], +m[2] - 1, +m[1]);
  return null;
}

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
      doBanco = { html: r.rows[0].v,
                  em: dataDaPagina(r.rows[0].v) || new Date(r.rows[0].updated_at || 0) };
    }
  } catch (e) {
    console.error('pagina: falha ao ler do banco —', e.message);
  }

  // ── candidata 2: arquivo publicado pelo repositório
  let doArquivo = null;
  try {
    const caminho = path.join(process.cwd(), 'public', alvo.arquivo);
    const conteudo = fs.readFileSync(caminho, 'utf8');
    doArquivo = { html: conteudo, em: dataDaPagina(conteudo) || fs.statSync(caminho).mtime };
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
