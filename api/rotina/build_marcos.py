# -*- coding: utf-8 -*-
"""
Gera marcos.html (Marcos & Metas) no padrao visual do painel-ole-vm
(Poppins, navy/laranja/dourado). Estrutura: big numbers -> atingimento
(donut + barras mensais) -> marcos por setor -> calendario -> regras.
Meta congelada no dia 0 (14/09/2026). Uso: python build_marcos.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(HERE, "marcos.json"), encoding="utf-8") as f:
    DATA = f.read()

TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Marcos &amp; Metas | Painel Olé V&amp;M</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
  :root {
    --navy: #1D3461; --blue-light: #2a4a8a;
    --gold: #E8A020; --gold-light: #f5c04a;
    --ole-orange: #E8622A; --vm-red: #7B1D1D;
    --green: #16a34a; --green-light: #22c55e;
    --amber: #d97706; --red: #dc2626;
    --bg: #f0f4f8; --surface: #ffffff; --surface2: #f8fafc;
    --border: #e2e8f0; --text: #1e293b; --text-muted: #64748b;
    --radius: 12px;
    --shadow: 0 4px 24px rgba(15,31,61,0.10);
    --shadow-lg: 0 8px 40px rgba(15,31,61,0.16);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family:'Poppins',sans-serif; background:var(--bg); color:var(--text); min-height:100vh; }
  header {
    background:#e8e8e8; padding:0 40px; display:flex; align-items:center;
    justify-content:space-between; height:72px; border-bottom:3px solid #e8600a;
    position:sticky; top:0; z-index:100; box-shadow:0 2px 16px rgba(0,0,0,.12);
  }
  .logo { display:flex; align-items:center; gap:14px; }
  .logo-mark { width:36px; height:36px; background:var(--gold); border-radius:8px;
    display:flex; align-items:center; justify-content:center; font-size:18px; color:var(--navy); font-weight:900; }
  .logo-text { font-size:18px; color:#1e3a6e; letter-spacing:.5px; font-weight:700; }
  .logo-sub { font-size:9.5px; color:#6b7c9e; letter-spacing:1.8px; text-transform:uppercase; margin-top:3px; font-weight:500; }
  .header-right { display:flex; align-items:center; gap:12px; }
  .mes-badge { background:var(--ole-orange); color:#fff; padding:5px 14px; border-radius:20px;
    font-size:12px; font-weight:700; letter-spacing:1px; text-transform:uppercase; }
  .apres-btn { background:#1e3a6e; color:#fff; border:none; padding:8px 18px; border-radius:8px;
    font-family:'Poppins',sans-serif; font-size:13px; font-weight:600; cursor:pointer; transition:all .2s; }
  .apres-btn:hover { background:var(--navy); transform:translateY(-1px); box-shadow:0 4px 12px rgba(37,99,235,.3); }
  main { max-width:1300px; margin:0 auto; padding:32px 24px; }

  .kpi-strip { display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:16px; margin-bottom:28px; }
  .kpi-card { background:var(--surface); border-radius:var(--radius); padding:20px 24px;
    box-shadow:var(--shadow); border-top:4px solid transparent; transition:transform .2s, box-shadow .2s; }
  .kpi-card:hover { transform:translateY(-2px); box-shadow:var(--shadow-lg); }
  .kpi-card.navy  { border-top-color:var(--navy); }
  .kpi-card.green { border-top-color:var(--green); }
  .kpi-card.gold  { border-top-color:var(--ole-orange); }
  .kpi-card.amber { border-top-color:var(--gold); }
  .kpi-label { font-size:11px; font-weight:600; letter-spacing:1.2px; text-transform:uppercase; color:var(--text-muted); margin-bottom:8px; }
  .kpi-value { font-size:36px; font-weight:800; color:var(--navy); line-height:1; }
  .kpi-sub { font-size:12px; color:var(--text-muted); margin-top:6px; }

  .section-title { font-size:20px; font-weight:700; color:var(--navy); margin:34px 0 6px; padding-bottom:10px;
    border-bottom:2px solid var(--ole-orange); display:flex; align-items:center; gap:10px; }
  .section-title span { font-size:12px; color:var(--text-muted); font-weight:400; }
  .section-sub { font-size:13px; color:var(--text-muted); margin:8px 0 18px; max-width:78ch; }

  .ating-grid { display:grid; grid-template-columns:minmax(280px,380px) 1fr; gap:16px; align-items:stretch; }
  @media (max-width:820px){ .ating-grid { grid-template-columns:1fr; } }
  .card { background:var(--surface); border-radius:var(--radius); padding:24px; box-shadow:var(--shadow); }
  .donut-wrap { display:flex; flex-direction:column; align-items:center; gap:10px; }
  .donut-legend { display:flex; flex-wrap:wrap; gap:12px 18px; justify-content:center; font-size:12px; color:var(--text-muted); }
  .donut-legend span { display:flex; align-items:center; gap:6px; font-weight:600; }
  .ldot { width:10px; height:10px; border-radius:3px; }
  .chart-title { font-size:13px; font-weight:700; color:var(--navy); letter-spacing:.5px; text-transform:uppercase; margin-bottom:14px; }
  .bars-note { font-size:11.5px; color:var(--text-muted); margin-top:10px; }

  .area-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:16px; }
  .area-card { background:var(--surface); border-radius:var(--radius); padding:22px 24px; box-shadow:var(--shadow); border-left:5px solid transparent; }
  .area-card.prosp { border-left-color:var(--ole-orange); }
  .area-card.leg   { border-left-color:var(--navy); }
  .area-card.np    { border-left-color:var(--gold); }
  .area-head { display:flex; align-items:baseline; justify-content:space-between; margin-bottom:2px; }
  .area-name { font-size:11px; font-weight:700; letter-spacing:1.2px; text-transform:uppercase; }
  .area-card.prosp .area-name { color:#c04a00; }
  .area-card.leg .area-name   { color:var(--navy); }
  .area-card.np .area-name    { color:#a07000; }
  .area-count { font-size:26px; font-weight:800; color:var(--navy); }
  .conf-line { display:flex; align-items:center; gap:8px; font-size:12px; color:var(--text-muted); margin:6px 0 12px; }
  .conf-pill { padding:2px 10px; border-radius:20px; font-size:11px; font-weight:700; }
  .conf-alta  { background:#dcfce7; color:#166534; }
  .conf-media { background:#fef3c7; color:#92400e; }
  .conf-baixa { background:#fee2e2; color:#991b1b; }
  .area-bar-wrap { height:8px; background:#e2e8f0; border-radius:99px; margin:0 0 14px; overflow:hidden; }
  .area-bar { height:100%; border-radius:99px; background:linear-gradient(90deg,var(--green),var(--green-light)); }
  .mlist { display:flex; flex-direction:column; }
  .mitem { display:flex; gap:10px; align-items:baseline; padding:6px 0; border-top:1px dashed var(--border); font-size:13px; }
  .mitem .dt { font-weight:700; color:var(--navy); min-width:50px; font-size:12.5px; }
  .mitem .nm { flex:1; }
  .mitem .pj { display:block; color:var(--text-muted); font-size:11px; }
  .sdot { width:9px; height:9px; border-radius:50%; flex:none; align-self:center; }
  .sdot.ok{background:var(--green-light)} .sdot.late{background:var(--red)}
  .sdot.and{background:var(--gold)} .sdot.prev{background:#94a3b8}

  .mes-sec { background:var(--surface); border-radius:var(--radius); box-shadow:var(--shadow); margin-bottom:18px; overflow:hidden; }
  .mes-sec.atual { outline:3px solid var(--gold-light); }
  .mes-head { display:flex; flex-wrap:wrap; align-items:center; gap:10px; padding:13px 20px; background:var(--navy); }
  .mes-head h3 { font-size:15px; color:#fff; font-weight:700; text-transform:capitalize; }
  .mes-head .tot { background:var(--ole-orange); color:#fff; border-radius:20px; font-size:11px; font-weight:700; padding:2px 10px; }
  .mes-head .tag-atual { background:var(--gold); color:var(--navy); border-radius:4px; font-size:10px; font-weight:800; padding:2px 8px; text-transform:uppercase; letter-spacing:.8px; }
  .mes-head .tot-ok { background:#22c55e; color:#fff; border-radius:20px; font-size:11px; font-weight:800; padding:2px 10px; }
  /* Barras do gráfico: cada mês abre o detalhe */
  .bar-g { cursor:pointer; }
  .bar-g:hover .bar-hit, .bar-g:focus .bar-hit { fill:#1d34610d; }
  .bar-g:focus { outline:none; }
  /* Janela com as metas do mês */
  .dm-fundo { display:none; position:fixed; inset:0; background:rgba(15,31,61,.5); z-index:90; padding:18px; overflow-y:auto; }
  .dm-fundo.aberto { display:flex; align-items:flex-start; justify-content:center; }
  .dm-caixa { background:var(--surface); border-radius:var(--radius); box-shadow:0 18px 50px rgba(0,0,0,.3);
    width:100%; max-width:780px; margin-top:6vh; overflow:hidden; }
  .dm-topo { display:flex; align-items:flex-start; gap:12px; padding:16px 20px; background:var(--navy); color:#fff; }
  .dm-topo h3 { font-size:17px; font-weight:800; text-transform:capitalize; }
  .dm-topo .dm-sub { font-size:12.5px; opacity:.9; margin-top:2px; }
  .dm-x { margin-left:auto; background:transparent; border:0; color:#fff; font-size:26px; line-height:1;
    cursor:pointer; padding:0 4px; border-radius:6px; }
  .dm-x:hover { background:rgba(255,255,255,.15); }
  .dm-corpo { padding:6px 0 14px; max-height:68vh; overflow-y:auto; }
  .dm-bloco-tit { font-size:11.5px; font-weight:800; letter-spacing:.5px; text-transform:uppercase;
    padding:12px 20px 6px; }
  .dm-bloco-tit.ok { color:#15803d; }
  .dm-bloco-tit.pend { color:#b45309; }
  .dm-item { display:flex; flex-wrap:wrap; align-items:center; gap:10px; padding:9px 20px; border-top:1px solid var(--border); }
  .dm-dia { font-size:12px; font-weight:800; color:var(--navy); background:var(--surface2);
    border-radius:6px; padding:3px 8px; white-space:nowrap; }
  .dm-txt { flex:1; min-width:180px; font-size:13px; }
  .dm-txt b { display:block; color:var(--ink); font-weight:700; }
  .dm-proj { font-size:11px; color:var(--muted); }
  .dm-vazio { padding:8px 20px 12px; font-size:12.5px; color:var(--muted); }
  .dep-pill { font-size:9.5px; font-weight:700; color:#8a5a00; background:#fdf6e6; border:1px solid var(--gold);
    border-radius:20px; padding:1px 8px; white-space:nowrap; }
  @media print { .dm-fundo { display:none !important; } }
  .mes-head .chips { display:flex; flex-wrap:wrap; gap:6px; margin-left:auto; }
  /* Metas já atingidas: recolhidas por padrão */
  .feitas-head { display:flex; align-items:center; gap:10px; padding:10px 20px; border-top:1px solid var(--border);
    background:#f0fdf4; cursor:pointer; user-select:none; font-size:13px; color:#166534; }
  .feitas-head:hover { background:#e7fbee; }
  .feitas-head .fh-ico { color:#22c55e; font-size:13px; transition:transform .15s; display:inline-block; }
  .feitas-head.aberto .fh-ico { transform:rotate(90deg); }
  .feitas-head .fh-txt { flex:1; min-width:0; }
  .feitas-head .fh-pct { background:#22c55e; color:#fff; border-radius:20px; font-size:11px; font-weight:800; padding:2px 10px; }
  .feitas-head .fh-ver { font-size:11px; font-weight:700; color:#15803d; text-decoration:underline; white-space:nowrap; }
  .feitas-corpo { display:none; }
  .feitas-corpo.aberto { display:block; }
  @media print { .feitas-corpo { display:block; } .feitas-head .fh-ver { display:none; } }
  .badge-area { display:inline-flex; padding:2px 10px; border-radius:20px; font-size:10px; font-weight:700; letter-spacing:.8px; text-transform:uppercase; }
  .badge-prosp { background:#fde8d8; color:#c04a00; }
  .badge-leg   { background:#dce8f5; color:#1e3a6e; }
  .badge-np    { background:#fff3cd; color:#a07000; }
  .badge-outro { background:#f1f5f9; color:#64748b; }
  .marco-row { display:flex; flex-wrap:wrap; align-items:center; gap:12px; padding:10px 20px; border-top:1px solid var(--border); border-left:4px solid transparent; }
  .marco-row:hover { background:var(--surface2); }
  .marco-row.prior { border-left-color:var(--ole-orange); background:linear-gradient(90deg,#e8622a0d,transparent 45%); }
  .prior-star { color:var(--ole-orange); font-size:12px; }
  .marco-dia { font-size:15px; font-weight:800; color:var(--navy); min-width:52px; }
  .marco-info { flex:1; min-width:220px; }
  .marco-nome { font-weight:600; font-size:13.5px; color:var(--navy); }
  .marco-proj { color:var(--text-muted); font-size:11.5px; }
  .pct-pill { display:inline-block; padding:2px 8px; border-radius:20px; font-size:11px; font-weight:700; min-width:44px; text-align:center; }
  .pct-high { background:#dcfce7; color:#166534; }
  .pct-mid  { background:#fef3c7; color:#92400e; }
  .pct-low  { background:#fee2e2; color:#991b1b; }
  .pct-none { background:#f1f5f9; color:#94a3b8; }
  .status-pill { display:inline-flex; align-items:center; gap:5px; padding:3px 10px; border-radius:20px; font-size:11px; font-weight:600; }
  .st-ok   { background:#dcfce7; color:#166534; }
  .st-late { background:#fee2e2; color:#991b1b; }
  .st-and  { background:#fef3c7; color:#92400e; }
  .st-prev { background:#f1f5f9; color:#64748b; }
  .desvio-pill { font-size:11px; font-weight:700; border-radius:20px; padding:2px 9px; }
  .desvio-mais { background:#fee2e2; color:#991b1b; }
  .desvio-menos{ background:#dcfce7; color:#166534; }

  .regras { background:var(--surface2); border:1px solid var(--border); border-radius:var(--radius);
    padding:18px 22px; font-size:12.5px; color:var(--text-muted); line-height:1.7; }
  .regras b { color:var(--navy); }
  footer { text-align:center; font-size:11.5px; color:var(--text-muted); padding:26px 20px 34px; }

  /* EMBUTIDO NO PAINEL (iframe): esconde o cabecalho repetido */
  html.embed header { display: none; }
  .embed-bar { display: none; }
  html.embed .embed-bar { display: flex; justify-content: flex-end; align-items: center; gap: 12px; margin: 0 0 16px; }
  html.embed main { padding-top: 18px; }

  /* IMPRESSAO / PDF */
  @media print {
    header { position: static; }
    .apres-btn { display: none; }
    .card, .area-card, .kpi-card, .mes-sec, .regras { break-inside: avoid; box-shadow: none; border: 1px solid var(--border); }
    .section-title { break-after: avoid; }
    .ating-grid { grid-template-columns: 1fr; }
  }

  /* MODO APRESENTACAO */
  body.apres .detalhe { display:none; }
  body.apres .kpi-value { font-size:52px; }
  body.apres main { max-width:1100px; }
</style></head>
<body>
<header>
  <div class="logo">
    <div class="logo-mark">O</div>
    <div><div class="logo-text">Olé Casas × Viana e Moura</div>
    <div class="logo-sub">Marcos &amp; Metas · Desenv. Imobiliário</div></div>
  </div>
  <div class="header-right">
    <span class="mes-badge" id="mesbadge"></span>
    <button class="apres-btn" onclick="document.body.classList.toggle('apres');this.textContent=document.body.classList.contains('apres')?'Voltar ao painel':'🎬 Apresentação'">🎬 Apresentação</button>
  </div>
</header>
<main>
  <div class="kpi-strip" id="kpis"></div>

  <div class="section-title">Atingimento da meta <span id="subting"></span></div>
  <div class="ating-grid">
    <div class="card donut-wrap">
      <div class="chart-title">Status dos marcos</div>
      <svg id="donut" width="230" height="230" viewBox="0 0 230 230"></svg>
      <div class="donut-legend" id="dleg"></div>
    </div>
    <div class="card">
      <div class="chart-title">Metas por mês · previsto × concluído</div>
      <svg id="bars" width="100%" height="270" viewBox="0 0 860 270" preserveAspectRatio="xMidYMid meet"></svg>
      <div class="bars-note">Cada barra é o total de marcos com meta no mês; a parte verde é o que já foi concluído. <b>Clique em um mês</b> para ver quais metas foram atingidas e quais não. Na primeira semana de cada mês atualizamos e medimos o desvio.</div>
    </div>
  </div>

  <div class="section-title">Os marcos de cada setor <span>as metas assumidas no dia 0 — 14/09/26</span></div>
  <p class="section-sub">Cada setor assumiu seus marcos com data congelada no dia 0. É contra essas datas que
  mediremos o desvio, mês a mês. O selo de confiança indica a chance de cumprir o conjunto no prazo.</p>
  <div class="area-grid" id="setores"></div>

  <div class="detalhe">
    <div class="section-title">Calendário mês a mês <span>★ = Condomínio Morada dos Sabiás, a prioridade do momento</span></div>
    <div id="cal"></div>

    <div class="section-title">Como calculamos a confiança <span>regras v1 — abertas a debate</span></div>
    <div class="regras">
      <b>Marco concluído</b> vale 100. <b>Meta vencida sem conclusão</b> vale 10.
      Nos demais, comparamos o <b>ritmo real</b> (% concluído) com o <b>ritmo esperado</b>
      (fração do tempo já decorrido entre o início e a meta): ritmo ≥ 100% do esperado ≈ 90 pontos,
      caindo por faixas até 20. Há bônus de +10 quando a folga passa de 60 dias e desconto de −10
      quando faltam menos de 15 dias com execução abaixo de 70%.
      <b>Alta ≥ 75 · Média 50–74 · Baixa &lt; 50.</b> A confiança do setor é a média dos seus marcos.
    </div>
  </div>
</main>
<footer id="foot"></footer>

<div class="dm-fundo" id="modal-mes" onclick="if(event.target===this)fecharMes()">
  <div class="dm-caixa" role="dialog" aria-modal="true" aria-labelledby="dm-titulo">
    <div class="dm-topo">
      <div>
        <h3 id="dm-titulo"></h3>
        <div class="dm-sub" id="dm-sub"></div>
      </div>
      <button class="dm-x" id="dm-fechar" onclick="fecharMes()" aria-label="Fechar">×</button>
    </div>
    <div class="dm-corpo" id="dm-corpo"></div>
  </div>
</div>

<script>
// Dentro do painel (iframe), o cabecalho proprio some e o badge/botao
// migram para uma barra fina no topo do conteudo.
if (window.self !== window.top) {
  document.documentElement.classList.add("embed");
  const bar = document.createElement("div");
  bar.className = "embed-bar";
  const hr = document.querySelector(".header-right");
  while (hr && hr.firstChild) bar.appendChild(hr.firstChild);
  const alvo = document.querySelector("main") || document.body;
  alvo.insertBefore(bar, alvo.firstChild);
}
const DADOS = __DATA__;
const MESES=["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"];
const MABR=["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"];
const HOJE=DADOS.hoje;
const PRIOR=p=>{p=(p||"").toUpperCase();
  if(p.includes("RIAMBURGO"))return 0; if(p.includes("CAUCAIA II"))return 3;
  if(p.includes("CAUCAIA"))return 1; if(p.includes("PS3 - 408"))return 2;
  if(p.includes("CONDOMÍNIO")||p.includes("MORADA DOS SABIÁS"))return 4; return 99;};
let M=DADOS.marcos.filter(m=>m.ugb!=="MACROFLUXO - VISÃO GERAL"&&m.meta);
function br(iso){if(!iso)return"";const[a,m,d]=iso.split("-");return d+"/"+m+"/"+a.slice(2);}
function brc(iso){return iso?iso.split("-")[2]+"/"+iso.split("-")[1]:"";}
function dias(a,b){return Math.round((new Date(b)-new Date(a))/864e5);}
function setKey(s){s=(s||"").toUpperCase();
  if(s.includes("PROSP"))return"prosp"; if(s.includes("LEGAL"))return"leg";
  if(s.includes("NOVOS")||s.includes("ARQUIT"))return"np"; return"outro";}
// Projetos que só andam depois de outro — a dependência fica visível para a
// meta não ser lida como atraso do time (decisão da Carol, 19/10/2026).
const DEPENDE={"CONDOMÍNIO TESTE":"depende da entrada do Morada dos Sabiás"};
function dep(m){
  const p=(m.projeto||"").toUpperCase();
  for(const k in DEPENDE) if(p.includes(k)) return DEPENDE[k];
  return "";}
function estado(m){
  if(m.pct>=100)return["ok","Concluído"];
  if(m.meta<HOJE)return["late","Atrasado"];
  if(m.pct>0)return["and","Em andamento"];
  return["prev","Previsto"];}
function confianca(m){
  if(m.pct>=100)return 100;
  if(m.meta<HOJE)return 10;
  const ini=m.inicio&&m.inicio<m.meta?m.inicio:DADOS.hoje;
  const total=Math.max(dias(ini,m.meta),1);
  const dec=Math.min(Math.max(dias(ini,HOJE),0),total);
  const esperado=dec/total;
  const ritmo=esperado>0?(m.pct/100)/esperado:1;
  let s= ritmo>=1?90 : ritmo>=.75?75 : ritmo>=.5?55 : ritmo>=.25?35 : 20;
  const folga=dias(HOJE,m.meta);
  if(folga>60)s+=10;
  if(folga<15&&m.pct<70)s-=10;
  return Math.min(95,Math.max(5,s));}
function confClass(v){return v>=75?["conf-alta","Alta"]:v>=50?["conf-media","Média"]:["conf-baixa","Baixa"];}
function esc(s){return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}
M.forEach(m=>m.conf=confianca(m));

const hoje=new Date(HOJE);
document.getElementById("mesbadge").textContent=MESES[hoje.getMonth()]+" "+hoje.getFullYear();
const conc=M.filter(m=>m.pct>=100).length;
const vencidos=M.filter(m=>m.meta<HOJE).length;
const noPrazo=M.filter(m=>m.meta<HOJE&&m.pct>=100).length;
const ating=vencidos?Math.round(100*noPrazo/vencidos):null;
const confMedia=Math.round(M.reduce((s,m)=>s+m.conf,0)/M.length);
const kpis=[
  ["navy","Marcos mapeados",M.length,"metas dos 3 setores até "+br(M.map(m=>m.meta).sort().slice(-1)[0])],
  ["green","Concluídos",conc,conc?Math.round(100*conc/M.length)+"% do total":"a jornada começa agora"],
  ["gold","Atingimento do prazo",ating===null?"—":ating+"%",ating===null?"nenhuma meta vencida ainda":noPrazo+" de "+vencidos+" metas vencidas no prazo"],
  ["amber","Confiança média",confMedia,confClass(confMedia)[1]+" · regras v1"]];
document.getElementById("kpis").innerHTML=kpis.map(([c,l,v,s])=>
  '<div class="kpi-card '+c+'"><div class="kpi-label">'+l+'</div><div class="kpi-value">'+v+'</div><div class="kpi-sub">'+s+'</div></div>').join("");
document.getElementById("subting").textContent="dia 0: 14/09/26 · atualizado "+br(DADOS.gerado_em.slice(0,10));
// Aviso de dado velho: se o export parar de chegar, isso aparece antes de alguém
// apresentar número vencido numa reunião.
(function(){
  var d = new Date(DADOS.gerado_em.slice(0,10));
  var dias = Math.floor((new Date() - d)/86400000);
  if (dias < 7) return;
  var el = document.createElement("div");
  el.style.cssText = "background:#fdecea;border:1px solid #D93025;border-left:5px solid #D93025;"+
    "border-radius:10px;padding:9px 13px;margin:10px 0;font-size:12.5px;color:#8B2020;font-weight:600";
  el.textContent = "⚠ Dados do Smartsheet de " + br(DADOS.gerado_em.slice(0,10)) + " — " + dias +
    " dias atrás. A atualização automática pode ter falhado.";
  var alvo = document.getElementById("subting");
  (alvo.closest("header") || alvo.parentNode).appendChild(el);
})();
document.getElementById("foot").textContent="Fonte: Smartsheet OLE VM - DEV IMOB · metas congeladas no dia 0 (14/09/2026) · retroalimentação na 1ª semana de cada mês · MACROFLUXO fora do escopo";

// DONUT
(function(){
  const cnt={ok:0,and:0,prev:0,late:0};
  M.forEach(m=>cnt[estado(m)[0]]++);
  const cores={ok:"#22c55e",and:"#E8A020",prev:"#94a3b8",late:"#dc2626"};
  const rot={ok:"Concluído",and:"Em andamento",prev:"Previsto",late:"Atrasado"};
  const svg=document.getElementById("donut");
  const cx=115,cy=115,r=88,w=30,total=M.length;
  let a0=-Math.PI/2,html="";
  ["ok","and","prev","late"].forEach(k=>{
    if(!cnt[k])return;
    const a1=a0+2*Math.PI*cnt[k]/total;
    const large=(a1-a0)>Math.PI?1:0;
    const x0=cx+r*Math.cos(a0),y0=cy+r*Math.sin(a0);
    const x1=cx+r*Math.cos(a1),y1=cy+r*Math.sin(a1);
    if(cnt[k]===total){ html+='<circle cx="'+cx+'" cy="'+cy+'" r="'+r+'" fill="none" stroke="'+cores[k]+'" stroke-width="'+w+'"/>'; }
    else html+='<path d="M '+x0+' '+y0+' A '+r+' '+r+' 0 '+large+' 1 '+x1+' '+y1+'" fill="none" stroke="'+cores[k]+'" stroke-width="'+w+'" stroke-linecap="butt"/>';
    a0=a1;
  });
  html+='<text x="'+cx+'" y="'+(cy-6)+'" text-anchor="middle" font-size="40" font-weight="800" fill="#1D3461" font-family="Poppins,sans-serif">'+total+'</text>';
  html+='<text x="'+cx+'" y="'+(cy+20)+'" text-anchor="middle" font-size="12" fill="#64748b" font-family="Poppins,sans-serif">marcos</text>';
  // percentual já atingido, discreto, embaixo do total
  if(cnt.ok)html+='<text x="'+cx+'" y="'+(cy+40)+'" text-anchor="middle" font-size="11.5" font-weight="700" fill="#15803d" font-family="Poppins,sans-serif">'+Math.round(100*cnt.ok/total)+'% atingido</text>';
  svg.innerHTML=html;
  document.getElementById("dleg").innerHTML=["ok","and","prev","late"].filter(k=>cnt[k])
    .map(k=>'<span><i class="ldot" style="background:'+cores[k]+'"></i>'+rot[k]+": "+cnt[k]+"</span>").join("");
})();

// BARRAS MENSAIS
(function(){
  const porMes={};
  M.forEach(m=>{const k=m.meta.slice(0,7);(porMes[k] ||= {t:0,c:0});porMes[k].t++;if(m.pct>=100)porMes[k].c++;});
  const keys=Object.keys(porMes).sort();
  const svg=document.getElementById("bars");
  const W=860,H=270,pad={l:34,r:10,t:16,b:40};
  const maxV=Math.max(...keys.map(k=>porMes[k].t));
  const bw=Math.min(46,(W-pad.l-pad.r)/keys.length*0.62);
  const step=(W-pad.l-pad.r)/keys.length;
  let html="";
  for(let g=0;g<=maxV;g+=Math.ceil(maxV/4)||1){
    const y=H-pad.b-(H-pad.t-pad.b)*g/maxV;
    html+='<line x1="'+pad.l+'" y1="'+y+'" x2="'+(W-pad.r)+'" y2="'+y+'" stroke="#e2e8f0"/>';
    html+='<text x="'+(pad.l-8)+'" y="'+(y+4)+'" text-anchor="end" font-size="11" fill="#94a3b8" font-family="Poppins,sans-serif">'+g+'</text>';
  }
  keys.forEach((k,i)=>{
    const{t,c}=porMes[k];
    const x=pad.l+step*i+(step-bw)/2;
    const hT=(H-pad.t-pad.b)*t/maxV, hC=(H-pad.t-pad.b)*c/maxV;
    const ehAtual=k===HOJE.slice(0,7);
    const[a,mn]=k.split("-");
    // cada mês é um grupo clicável (a faixa invisível cobre a coluna inteira)
    html+='<g class="bar-g" data-m="'+k+'" role="button" tabindex="0">'+
      '<title>'+MESES[+mn-1]+' '+a+' — clique para ver as metas</title>'+
      '<rect class="bar-hit" x="'+(pad.l+step*i)+'" y="'+pad.t+'" width="'+step+'" height="'+(H-pad.t-pad.b+22)+'" fill="transparent"/>';
    html+='<rect x="'+x+'" y="'+(H-pad.b-hT)+'" width="'+bw+'" height="'+hT+'" rx="6" fill="'+(ehAtual?"#2a4a8a":"#1D3461")+'" opacity="'+(ehAtual?1:.82)+'"/>';
    if(c)html+='<rect x="'+x+'" y="'+(H-pad.b-hC)+'" width="'+bw+'" height="'+hC+'" rx="6" fill="#22c55e"/>';
    html+='<text x="'+(x+bw/2)+'" y="'+(H-pad.b-hT-6)+'" text-anchor="middle" font-size="12" font-weight="700" fill="#1D3461" font-family="Poppins,sans-serif">'+t+'</text>';
    html+='<text x="'+(x+bw/2)+'" y="'+(H-pad.b+16)+'" text-anchor="middle" font-size="11" fill="'+(ehAtual?"#E8622A":"#64748b")+'" font-weight="'+(ehAtual?800:500)+'" font-family="Poppins,sans-serif">'+MABR[+mn-1]+"/"+a.slice(2)+'</text>';
    // % atingido do mês, discreto, logo abaixo do rótulo
    if(c)html+='<text x="'+(x+bw/2)+'" y="'+(H-pad.b+30)+'" text-anchor="middle" font-size="10" font-weight="700" fill="#15803d" font-family="Poppins,sans-serif">'+Math.round(100*c/t)+'%</text>';
    html+='</g>';
  });
  svg.innerHTML=html;
  svg.addEventListener("click",e=>{const g=e.target.closest("g[data-m]");if(g)abrirMes(g.dataset.m);});
  svg.addEventListener("keydown",e=>{
    if(e.key!=="Enter"&&e.key!==" ")return;
    const g=e.target.closest("g[data-m]"); if(g){e.preventDefault();abrirMes(g.dataset.m);}});
})();

// DETALHE DO MÊS (clique na barra) — o que foi atingido e o que não foi
function abrirMes(ym){
  const[a,mn]=ym.split("-");
  const l=M.filter(m=>m.meta.slice(0,7)===ym)
    .sort((x,y)=>x.meta.localeCompare(y.meta)||x.projeto.localeCompare(y.projeto));
  if(!l.length)return;
  const feitas=l.filter(m=>m.pct>=100), abertas=l.filter(m=>m.pct<100);
  const pct=Math.round(100*feitas.length/l.length);
  const item=(m)=>{
    const[st,rot]=estado(m); const dv=m.desvio_dias;
    return'<div class="dm-item"><span class="dm-dia">'+brc(m.meta)+'</span>'+
      '<span class="dm-txt"><b>'+esc(m.marco)+'</b><span class="dm-proj">'+esc(m.projeto)+' · '+esc(m.ugb)+(dep(m)?' <span class="dep-pill">⛓ '+dep(m)+'</span>':'')+'</span></span>'+
      '<span class="badge-area badge-'+setKey(m.setor)+'">'+esc(m.setor||"Geral")+'</span>'+
      '<span class="pct-pill '+(m.pct>=100?"pct-high":m.pct>=50?"pct-mid":m.pct>0?"pct-low":"pct-none")+'">'+m.pct+'%</span>'+
      '<span class="status-pill st-'+st+'">'+rot+'</span>'+
      (dv?'<span class="desvio-pill '+(dv>0?"desvio-mais":"desvio-menos")+'">'+(dv>0?"+":"")+dv+'d</span>':'')+
      '</div>';};
  const bloco=(titulo,cls,arr,vazio)=>'<div class="dm-bloco"><div class="dm-bloco-tit '+cls+'">'+titulo+' · '+arr.length+'</div>'+
    (arr.length?arr.map(item).join(""):'<div class="dm-vazio">'+vazio+'</div>')+'</div>';
  document.getElementById("dm-titulo").textContent=MESES[+mn-1]+" "+a;
  document.getElementById("dm-sub").innerHTML='<b>'+feitas.length+' de '+l.length+'</b> '+
    (l.length>1?"metas atingidas":"meta atingida")+' · '+pct+'%';
  document.getElementById("dm-corpo").innerHTML=
    bloco("✅ Atingidas","ok",feitas,"Nenhuma meta atingida neste mês ainda.")+
    bloco("⏳ Não atingidas","pend",abertas,"Todas as metas do mês foram atingidas. 🎉");
  document.getElementById("modal-mes").classList.add("aberto");
  document.getElementById("dm-fechar").focus();
}
function fecharMes(){document.getElementById("modal-mes").classList.remove("aberto");}
document.addEventListener("keydown",e=>{if(e.key==="Escape")fecharMes();});

// SETORES
(function(){
  const ordem=["PROSPECÇÃO","LEGALIZAÇÃO","NOVOS PRODUTOS"];
  const porSetor={};
  M.forEach(m=>{const s=(m.setor||"GERAL").toUpperCase();(porSetor[s] ||= []).push(m);});
  const chaves=Object.keys(porSetor).sort((a,b)=>{
    const ia=ordem.findIndex(o=>a.includes(o.split(" ")[0]));
    const ib=ordem.findIndex(o=>b.includes(o.split(" ")[0]));
    return(ia<0?99:ia)-(ib<0?99:ib)||a.localeCompare(b);});
  document.getElementById("setores").innerHTML=chaves.map(s=>{
    const l=porSetor[s].sort((a,b)=>a.meta.localeCompare(b.meta));
    const okn=l.filter(m=>m.pct>=100).length;
    const conf=Math.round(l.reduce((x,m)=>x+m.conf,0)/l.length);
    const[cc,cl]=confClass(conf);
    const itens=l.map(m=>{const[st]=estado(m);
      return'<div class="mitem"><i class="sdot '+st+'"></i><span class="dt">'+brc(m.meta)+'</span>'+
      '<span class="nm">'+esc(m.marco)+'<span class="pj">'+esc(m.projeto)+'</span></span></div>';}).join("");
    return'<div class="area-card '+setKey(s)+'"><div class="area-head">'+
      '<span class="area-name">'+esc(s)+'</span><span class="area-count">'+l.length+'</span></div>'+
      '<div class="conf-line">Confiança: <span class="conf-pill '+cc+'">'+cl+' · '+conf+'</span>'+
      (okn?'<span>· '+okn+' concluído'+(okn>1?'s':'')+'</span>':'')+'</div>'+
      '<div class="area-bar-wrap"><div class="area-bar" style="width:'+Math.round(100*okn/l.length)+'%"></div></div>'+
      '<div class="mlist detalhe">'+itens+'</div></div>';}).join("");
})();

// CALENDARIO
(function(){
  const porMes={};
  M.forEach(m=>{(porMes[m.meta.slice(0,7)] ||= []).push(m);});
  document.getElementById("cal").innerHTML=Object.keys(porMes).sort().map(ym=>{
    const[a,mn]=ym.split("-");
    const ehAtual=ym===HOJE.slice(0,7);
    const l=porMes[ym].sort((x,y)=>x.meta.localeCompare(y.meta)||
      PRIOR(x.projeto)-PRIOR(y.projeto)||x.projeto.localeCompare(y.projeto));
    const porSetor={};
    l.forEach(m=>{const s=m.setor||"Geral";porSetor[s]=(porSetor[s]||0)+1;});
    const chips=Object.entries(porSetor).map(([s,n])=>
      '<span class="badge-area badge-'+setKey(s)+'">'+esc(s)+': '+n+'</span>').join("");
    const linha=(m)=>{
      const[st,rot]=estado(m);
      const pctCls=m.pct>=100?"pct-high":m.pct>=50?"pct-mid":m.pct>0?"pct-low":"pct-none";
      const dv=m.desvio_dias;
      const ehPrior=/CONDOMÍNIO|MORADA DOS SABIÁS/.test((m.projeto||"").toUpperCase());
      return'<div class="marco-row'+(ehPrior?" prior":"")+'"><span class="marco-dia">'+brc(m.meta)+'</span>'+
        '<span class="marco-info"><span class="marco-nome">'+(ehPrior?'<span class="prior-star" title="Projeto prioritário">★</span> ':'')+esc(m.marco)+'</span><br>'+
        '<span class="marco-proj">'+esc(m.projeto)+' · '+esc(m.ugb)+(dep(m)?' <span class="dep-pill">⛓ '+dep(m)+'</span>':'')+'</span></span>'+
        '<span class="badge-area badge-'+setKey(m.setor)+'">'+esc(m.setor||"Geral")+'</span>'+
        '<span class="pct-pill '+pctCls+'">'+m.pct+'%</span>'+
        '<span class="status-pill st-'+st+'">'+rot+'</span>'+
        (dv?'<span class="desvio-pill '+(dv>0?"desvio-mais":"desvio-menos")+'">'+(dv>0?"+":"")+dv+'d</span>':'')+
        '</div>';};
    // Metas já batidas ficam recolhidas: o mês mostra só quantas foram atingidas.
    const feitas=l.filter(m=>m.pct>=100), abertas=l.filter(m=>m.pct<100);
    const pctMes=Math.round(100*feitas.length/l.length);
    const idg="g"+ym.replace("-","");
    const grupo=feitas.length?
      '<div class="feitas-head" data-g="'+idg+'" id="h'+idg+'">'+
        '<span class="fh-ico">▸</span>'+
        '<span class="fh-txt"><b>'+feitas.length+' de '+l.length+'</b> '+(l.length>1?"metas atingidas":"meta atingida")+' neste mês</span>'+
        '<span class="fh-pct">'+pctMes+'%</span>'+
        '<span class="fh-ver">ver metas</span>'+
      '</div><div class="feitas-corpo" id="'+idg+'">'+feitas.map(linha).join("")+'</div>':"";
    return'<section class="mes-sec'+(ehAtual?" atual":"")+'"><div class="mes-head"><h3>'+MESES[+mn-1]+" "+a+'</h3>'+
      '<span class="tot">'+l.length+'</span>'+(ehAtual?'<span class="tag-atual">mês atual</span>':"")+
      (feitas.length?'<span class="tot-ok">✓ '+feitas.length+'</span>':"")+
      '<div class="chips">'+chips+'</div></div>'+grupo+abertas.map(linha).join("")+'</section>';}).join("");
})();

// Abre/fecha o bloco de metas já atingidas do mês
document.getElementById("cal").addEventListener("click",function(e){
  const h=e.target.closest(".feitas-head");
  if(!h)return;
  const c=document.getElementById(h.dataset.g);
  const aberto=c.classList.toggle("aberto");
  h.classList.toggle("aberto",aberto);
  h.querySelector(".fh-ver").textContent=aberto?"ocultar":"ver metas";
});
</script>
</body></html>
"""

html = TEMPLATE.replace("__DATA__", DATA)
dest = os.path.join(HERE, "marcos.html")
with open(dest, "w", encoding="utf-8") as f:
    f.write(html)
print("Gerado:", dest, len(html), "bytes")
