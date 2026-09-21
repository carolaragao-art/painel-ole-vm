// Alerta automático de Certidões e Licenças (aba Processos · Órgãos).
// Roda todo dia via Vercel Cron (vercel.json). Lê 'ole_certs' no banco,
// detecta documentos VENCIDOS ou na janela de RENOVAR e envia e-mail para
// a caixa do setor dizendo qual é a licença e por que atualizar.
//
// Envio: Resend (env RESEND_API_KEY). Sem a chave, responde com a prévia
// do que seria enviado (pending: true) — útil para testar com ?dry=1.
// Estado anti-spam na chave 'ole_certs_alertas': reenvia quando o status
// muda ou a cada 7 dias enquanto o documento seguir vencido.
import { getAllState, setState } from '../../lib/db';
import { getSession } from '../../lib/auth';

const DESTINO = process.env.ALERTA_TO || 'desenvolvimentoimobole@vianaemoura.com.br';
const REMETENTE = process.env.ALERTA_FROM || 'Painel Olé VM <onboarding@resend.dev>';
const REENVIO_DIAS = 7;

function br(iso) {
  if (!iso) return '—';
  const [a, m, d] = String(iso).slice(0, 10).split('-');
  return `${d}/${m}/${a}`;
}

function statusDe(item, hoje) {
  const man = String(item.statusManual || '').toUpperCase();
  if (man === 'EM ANDAMENTO' || man === 'SUSPENSO') return { key: man, dias: null };
  if (!item.vencimento) return { key: 'SEM DATA', dias: null };
  const dias = Math.round((new Date(item.vencimento + 'T00:00:00') - hoje) / 86400000);
  if (dias < 0) return { key: 'VENCIDA', dias };
  if (dias <= (Number(item.antecedencia) || 0)) return { key: 'RENOVAR', dias };
  return { key: 'ATUALIZADA', dias };
}

function autorizado(req) {
  if (getSession(req)) return true;
  const ua = String(req.headers['user-agent'] || '');
  if (ua.startsWith('vercel-cron')) return true;
  const auth = String(req.headers['authorization'] || '');
  if (process.env.CRON_SECRET && auth === `Bearer ${process.env.CRON_SECRET}`) return true;
  return false;
}

export default async function handler(req, res) {
  if (!autorizado(req)) {
    res.status(401).json({ error: 'nao autorizado' });
    return;
  }
  const dry = String(req.query.dry || '') === '1';

  try {
    const state = await getAllState();
    let grupos = [];
    try { grupos = JSON.parse(state.ole_certs || '[]'); } catch (e) { grupos = []; }
    let memoria = {};
    try { memoria = JSON.parse(state.ole_certs_alertas || '{}'); } catch (e) { memoria = {}; }

    const hoje = new Date(); hoje.setHours(0, 0, 0, 0);
    const agora = Date.now();
    const alertas = [];

    for (const g of Array.isArray(grupos) ? grupos : []) {
      for (const item of Array.isArray(g.itens) ? g.itens : []) {
        const st = statusDe(item, hoje);
        const chave = `${g.id}:${item.id}`;
        const mem = memoria[chave] || {};
        const critico = st.key === 'VENCIDA' || st.key === 'RENOVAR';

        let enviar = false;
        if (critico && mem.status !== st.key) enviar = true;               // mudou de status
        else if (st.key === 'VENCIDA' && mem.enviadoEm &&
                 agora - mem.enviadoEm > REENVIO_DIAS * 86400000) enviar = true; // lembrete semanal

        if (critico) {
          const motivo = st.key === 'VENCIDA'
            ? `Vencida há ${Math.abs(st.dias)} dia(s) — o documento perdeu a validade e precisa ser renovado imediatamente para não travar protocolos e processos que dependem dele.`
            : `Vence em ${st.dias} dia(s) e a antecedência cadastrada é de ${Number(item.antecedencia) || 0} dias — a renovação precisa começar agora para ficar pronta antes do vencimento.`;
          alertas.push({ chave, enviar, grupo: g.nome || '', nome: item.nome || '',
            orgao: item.orgao || '', cidade: item.cidade || '',
            vencimento: item.vencimento || '', status: st.key, dias: st.dias,
            motivo, finalidade: item.finalidade || '', link: item.link || '' });
        }
        memoria[chave] = { status: st.key, enviadoEm: mem.enviadoEm || null };
      }
    }

    const paraEnviar = alertas.filter(a => a.enviar);
    if (!paraEnviar.length) {
      res.status(200).json({ ok: true, enviados: 0, monitorados: alertas.length, dry });
      return;
    }

    const linhas = paraEnviar.map(a => `
      <tr>
        <td style="padding:8px 10px;border-bottom:1px solid #e2e8f0"><b>${a.nome}</b><br>
            <span style="color:#64748b;font-size:12px">${a.grupo}${a.cidade ? ' · ' + a.cidade : ''}</span></td>
        <td style="padding:8px 10px;border-bottom:1px solid #e2e8f0">${a.orgao}</td>
        <td style="padding:8px 10px;border-bottom:1px solid #e2e8f0">${br(a.vencimento)}</td>
        <td style="padding:8px 10px;border-bottom:1px solid #e2e8f0;color:${a.status === 'VENCIDA' ? '#dc2626' : '#d97706'};font-weight:700">${a.status}</td>
        <td style="padding:8px 10px;border-bottom:1px solid #e2e8f0">${a.motivo}${a.finalidade ? '<br><span style="color:#64748b;font-size:12px">Finalidade: ' + a.finalidade + '</span>' : ''}</td>
      </tr>`).join('');

    const vencidas = paraEnviar.filter(a => a.status === 'VENCIDA').length;
    const assunto = `⚠ Certidões e Licenças: ${vencidas ? vencidas + ' vencida(s)' : ''}${vencidas && paraEnviar.length > vencidas ? ' e ' : ''}${paraEnviar.length > vencidas ? (paraEnviar.length - vencidas) + ' para renovar' : ''} — Painel Desenv. Imob`;
    const html = `
      <div style="font-family:'Segoe UI',Arial,sans-serif;color:#1e293b;max-width:720px">
        <h2 style="color:#1D3461;border-bottom:3px solid #E8622A;padding-bottom:8px">Alerta de Certidões e Licenças</h2>
        <p>Os documentos abaixo precisam de ação, segundo a aba <b>Processos · Órgãos</b> do painel:</p>
        <table style="border-collapse:collapse;width:100%;font-size:13.5px">
          <tr style="background:#1D3461;color:#fff;text-align:left">
            <th style="padding:8px 10px">Certidão / Licença</th><th style="padding:8px 10px">Órgão</th>
            <th style="padding:8px 10px">Vencimento</th><th style="padding:8px 10px">Status</th>
            <th style="padding:8px 10px">Por que atualizar</th></tr>
          ${linhas}
        </table>
        <p style="margin-top:16px"><a href="https://painel-ole-vm.vercel.app/" style="color:#1D3461;font-weight:700">Abrir o painel →</a></p>
        <p style="color:#94a3b8;font-size:12px">Alerta automático diário do Painel Olé V&amp;M · reenvio semanal enquanto houver documento vencido.</p>
      </div>`;

    if (dry) {
      res.status(200).json({ ok: true, dry: true, enviaria: paraEnviar, assunto });
      return;
    }

    if (!process.env.RESEND_API_KEY) {
      res.status(200).json({ ok: false, pending: true,
        motivo: 'RESEND_API_KEY nao configurada na Vercel', enviaria: paraEnviar });
      return;
    }

    const resp = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${process.env.RESEND_API_KEY}`,
                 'Content-Type': 'application/json' },
      body: JSON.stringify({ from: REMETENTE, to: [DESTINO], subject: assunto, html }),
    });
    const corpo = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      res.status(502).json({ ok: false, erro: corpo });
      return;
    }

    const ts = Date.now();
    for (const a of paraEnviar) memoria[a.chave] = { status: a.status, enviadoEm: ts };
    await setState('ole_certs_alertas', JSON.stringify(memoria));

    res.status(200).json({ ok: true, enviados: paraEnviar.length, id: corpo.id });
  } catch (e) {
    console.error('Erro /api/alerta-certs:', e.message);
    res.status(500).json({ error: 'erro interno' });
  }
}
