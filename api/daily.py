# -*- coding: utf-8 -*-
"""Dailys por e-mail — cron da Vercel (vercel.json), todo dia ~07:30 Fortaleza.

Diário  -> caixa do setor (DAILY_TO): atividades que vencem hoje e as que
           viraram atrasadas, nos setores Prospecção/Legalização/Novos Produtos.
Segunda -> e-mail da Carol (SEMANAL_TO): marcos que precisam de atenção
           (vencidos, com desvio ou andando devagar) e atrasados por projeto,
           para o replanejamento.

Dados: chaves dados_atividades / dados_marcos gravadas por api/importar.py a
cada export. Envio: SMTP Gmail com SMTP_USER/SMTP_PASSWORD (senha de app).
Teste sem enviar: GET /api/daily?dry=1&token=<IMPORT_TOKEN>.
"""
from http.server import BaseHTTPRequestHandler
import json
import os
import smtplib
import ssl
import traceback
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

FORTALEZA = timezone(timedelta(hours=-3))
DAILY_TO = os.environ.get("DAILY_TO", "desenvolvimentoimobole@vianaemoura.com.br")
SEMANAL_TO = os.environ.get("SEMANAL_TO", "carolaragao@olecasas.com.br")
FOCO = ("PROSP", "LEGAL", "NOVOS")
FORA = ("MACROFLUXO", "MODELO")
PROJ_FORA = ("PS4 - T+1",)

MA = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def br(iso):
    if not iso:
        return "—"
    a, m, d = str(iso)[:10].split("-")
    return f"{d}/{MA[int(m)-1]}"


def conectar():
    import pg8000.dbapi
    from urllib.parse import urlparse, unquote
    url = (os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
           or os.environ.get("POSTGRES_URL_NON_POOLING") or "")
    u = urlparse(url)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return pg8000.dbapi.connect(
        user=unquote(u.username or ""), password=unquote(u.password or ""),
        host=u.hostname, port=u.port or 5432,
        database=(u.path or "/").lstrip("/").split("?")[0], ssl_context=ctx)


def ler(cur, k):
    cur.execute("SELECT v FROM rotina_painel WHERE k = %s", (k,))
    linha = cur.fetchone()
    return linha[0] if linha else None


def foco(x):
    s = (x.get("setor") or "").upper()
    if not any(f in s for f in FOCO):
        return False
    if any(f in (x.get("ugb") or "").upper() for f in FORA):
        return False
    if (x.get("projeto") or "") in PROJ_FORA:
        return False
    return True


def grupo_de(x):
    """Nível entre o setor e a atividade (ex.: 'DVT de esgoto') — pedido da
    Carol em 09/11/2026 para localizar a atividade dentro do processo."""
    g = (x.get("grupo") or "").strip()
    return f" <span style='color:#64748b'>· {g}</span>" if g else ""


def linha_atv(x, com_data=False):
    pct = f" ({x['pct']}%)" if x.get("pct") else ""
    data = f" — venceu {br(x['termino'])}" if com_data else ""
    return (f"<li><b>{x['projeto']}</b> · {x['setor'].title()}{grupo_de(x)}: "
            f"{x['atividade']}{pct}{data}</li>")


def prioridade_projeto(p):
    p = (p or "").upper()
    if "SABI" in p or "CONDOMÍNIO MORADA" in p:
        return 0
    if "RIAMBURGO" in p:
        return 1
    if "CAUCAIA II" in p:
        return 4
    if "CAUCAIA" in p:
        return 2
    if "PS3 - 408" in p:
        return 3
    if "TESTE" in p or "PS3 - CONDOM" in p:
        return 5
    return 9


def monta_daily(atv, marcos, hoje):
    """Daily agrupada por PROJETO (pedido da Carol, 09/11/2026)."""
    hj = hoje.isoformat()
    ontem = (hoje - timedelta(days=1)).isoformat()
    sem_fim = (hoje + timedelta(days=(6 - hoje.weekday()))).isoformat()
    tudo = [x for x in sum(atv["atividades"].values(), []) if foco(x)]
    ms = [m for m in marcos["marcos"]
          if not any(f in (m.get("ugb") or "").upper() for f in FORA)
          and (m.get("projeto") or "") not in PROJ_FORA]

    blocos = {}

    def bloco(proj):
        return blocos.setdefault(proj, {"hoje": [], "semana": [], "atrasou": [], "marcos": []})

    n_hoje = n_atr = 0
    for x in tudo:
        t, pct = x.get("termino"), (x.get("pct") or 0)
        if t == hj:
            bloco(x["projeto"])["hoje"].append(x)
            n_hoje += 1
        elif t == ontem and pct < 100:
            bloco(x["projeto"])["atrasou"].append(x)
            n_atr += 1
        elif t and hj < t <= sem_fim and pct < 100:
            bloco(x["projeto"])["semana"].append(x)
    for m in ms:
        if m.get("meta") and hj <= m["meta"] <= sem_fim and (m.get("pct") or 0) < 100:
            bloco(m["projeto"])["marcos"].append(m)

    corpo = [f"<h2 style='color:#1D3461;border-bottom:3px solid #E8622A;"
             f"padding-bottom:6px'>Daily DI · {hoje.strftime('%d/%m/%Y')}</h2>"]
    if not blocos:
        corpo.append("<p>Sem vencimentos hoje nem na semana, nos 3 setores.</p>")

    def li(x, pref=""):
        pct = f" ({x['pct']}%)" if x.get("pct") else ""
        return f"<li>{pref}{x['setor'].title()}{grupo_de(x)}: {x['atividade']}{pct}</li>"

    for proj in sorted(blocos, key=lambda p: (prioridade_projeto(p), p)):
        b = blocos[proj]
        corpo.append(
            f"<h3 style='background:#1D3461;color:#fff;padding:7px 12px;"
            f"border-radius:6px;margin:18px 0 6px'>{proj}</h3>")
        itens = []
        for x in b["hoje"]:
            itens.append(li(x, "<b style='color:#E8622A'>HOJE</b> · "))
        for x in b["atrasou"]:
            itens.append(li(x, "<b style='color:#dc2626'>⚠ ATRASOU ONTEM</b> · "))
        for x in sorted(b["semana"], key=lambda z: z["termino"]):
            itens.append(li(x, f"<b>{br(x['termino'])}</b> · "))
        if itens:
            corpo.append("<ul style='margin:4px 0 6px'>" + "".join(itens) + "</ul>")
        if b["marcos"]:
            corpo.append("<p style='margin:2px 0 4px'>" + " ".join(
                f"<span style='border:1.5px solid #E8A020;border-radius:12px;"
                f"padding:2px 10px;font-size:13px'>🎯 {m['marco']} · "
                f"<b>{br(m['meta'])}</b> · {m.get('pct', 0)}%</span>"
                for m in sorted(b["marcos"], key=lambda z: z["meta"])) + "</p>")

    corpo.append("<p style='margin-top:14px'><a href='https://painel-ole-vm.vercel.app/' "
                 "style='color:#1D3461;font-weight:bold'>Abrir o painel →</a></p>")
    assunto = f"Daily DI · {hoje.strftime('%d/%m')} — {n_hoje} para hoje" + (
        f" · {n_atr} novas atrasadas" if n_atr else "")
    return assunto, "".join(corpo), bool(blocos)


def monta_segunda(atv, marcos, hoje):
    hj = hoje.isoformat()
    ms = [m for m in marcos["marcos"]
          if not any(f in (m.get("ugb") or "").upper() for f in FORA)]
    vencidos = [m for m in ms if m.get("meta") and m["meta"] < hj and (m.get("pct") or 0) < 100]
    horizonte = (hoje + timedelta(days=30)).isoformat()
    atencao = [m for m in ms if m.get("meta") and hj <= m["meta"] <= horizonte
               and (m.get("pct") or 0) < 50]
    desvios = [m for m in ms if (m.get("desvio_dias") or 0) > 0 and (m.get("pct") or 0) < 100]
    atrasadas = [x for x in atv["atividades"].get("atrasadas", []) if foco(x)]

    def li_marco(m, extra=""):
        return (f"<li><b>{m['marco']}</b> ({m['projeto']} · {m['setor'].title()}) — "
                f"meta {br(m['meta'])} · {m.get('pct', 0)}%{extra}</li>")

    corpo = [f"<h2 style='color:#1D3461;border-bottom:3px solid #E8622A;"
             f"padding-bottom:6px'>Replanejamento semanal · {hoje.strftime('%d/%m/%Y')}</h2>"]
    if vencidos:
        corpo.append("<h3 style='color:#dc2626'>⚠ Marcos vencidos</h3><ul>"
                     + "".join(li_marco(m) for m in sorted(vencidos, key=lambda z: z["meta"])) + "</ul>")
    if desvios:
        corpo.append("<h3 style='color:#d97706'>↔ Marcos com desvio vs dia 0</h3><ul>"
                     + "".join(li_marco(m, f" · <b>+{m['desvio_dias']}d</b>")
                               for m in sorted(desvios, key=lambda z: -z["desvio_dias"])) + "</ul>")
    if atencao:
        corpo.append("<h3 style='color:#1D3461'>👀 Vencem em até 30 dias com menos de 50%</h3><ul>"
                     + "".join(li_marco(m) for m in sorted(atencao, key=lambda z: z["meta"])) + "</ul>")
    if atrasadas:
        por_proj = {}
        for x in atrasadas:
            por_proj.setdefault(x["projeto"], []).append(x)
        corpo.append("<h3 style='color:#dc2626'>📋 Atividades atrasadas por projeto</h3>")
        for p in sorted(por_proj, key=lambda k: -len(por_proj[k])):
            corpo.append(f"<p style='margin:8px 0 2px'><b>{p}</b> ({len(por_proj[p])})</p><ul>"
                         + "".join(f"<li>{x['atividade']} — {x['setor'].title()} · "
                                   f"venceu {br(x['termino'])} · {x.get('pct', 0)}%</li>"
                                   for x in sorted(por_proj[p], key=lambda z: z["termino"]))
                         + "</ul>")
    corpo.append("<p><a href='https://painel-ole-vm.vercel.app/' "
                 "style='color:#1D3461;font-weight:bold'>Abrir o painel →</a></p>")
    assunto = (f"Replanejamento DI · semana de {hoje.strftime('%d/%m')} — "
               f"{len(vencidos)} vencido(s), {len(atrasadas)} atrasada(s)")
    return assunto, "".join(corpo)


def enviar(destino, assunto, html):
    user = os.environ.get("SMTP_USER") or os.environ.get("GMAIL_USER")
    pwd = os.environ.get("SMTP_PASSWORD") or os.environ.get("GMAIL_APP_PASSWORD")
    if not user or not pwd:
        return False, "SMTP_USER/SMTP_PASSWORD nao configurados na Vercel"
    msg = MIMEText(f"<div style=\"font-family:'Segoe UI',Arial,sans-serif;"
                   f"color:#1e293b;max-width:720px\">{html}</div>", "html", "utf-8")
    msg["Subject"] = assunto
    msg["From"] = f"Painel Olé VM <{user}>"
    msg["To"] = destino
    with smtplib.SMTP_SSL(os.environ.get("SMTP_HOST", "smtp.gmail.com"),
                          int(os.environ.get("SMTP_PORT", 465))) as s:
        s.login(user, pwd)
        s.sendmail(user, [d.strip() for d in destino.split(",")], msg.as_string())
    return True, "ok"


class handler(BaseHTTPRequestHandler):
    def responder(self, codigo, dados):
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        try:
            from urllib.parse import parse_qs
            q = parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
            dry = (q.get("dry") or ["0"])[0] == "1"
            token = (q.get("token") or [""])[0]
            ua = self.headers.get("user-agent", "")

            con = conectar()
            cur = con.cursor()
            esperado = ler(cur, "import_token") or os.environ.get("IMPORT_TOKEN", "")
            if not ua.startswith("vercel-cron") and (not esperado or token != esperado):
                cur.close(); con.close()
                return self.responder(401, {"erro": "nao autorizado"})

            atv = json.loads(ler(cur, "dados_atividades") or "{}")
            marcos = json.loads(ler(cur, "dados_marcos") or "{}")
            cur.close(); con.close()
            if not atv or not marcos:
                return self.responder(409, {"erro": "dados ausentes — rode um import antes"})

            hoje = datetime.now(FORTALEZA).date()
            saida = {"hoje": hoje.isoformat(), "dry": dry, "envios": []}

            assunto, html, tem = monta_daily(atv, marcos, hoje)
            if tem:
                if dry:
                    saida["envios"].append({"para": DAILY_TO, "assunto": assunto})
                else:
                    ok, info = enviar(DAILY_TO, assunto, html)
                    saida["envios"].append({"para": DAILY_TO, "assunto": assunto,
                                            "ok": ok, "info": info})

            if hoje.weekday() == 0:  # segunda-feira
                assunto2, html2 = monta_segunda(atv, marcos, hoje)
                if dry:
                    saida["envios"].append({"para": SEMANAL_TO, "assunto": assunto2})
                else:
                    ok, info = enviar(SEMANAL_TO, assunto2, html2)
                    saida["envios"].append({"para": SEMANAL_TO, "assunto": assunto2,
                                            "ok": ok, "info": info})

            self.responder(200, saida)
        except Exception as e:
            self.responder(500, {"erro": str(e), "trace": traceback.format_exc()[-1000:]})
