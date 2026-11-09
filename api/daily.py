# -*- coding: utf-8 -*-
"""E-mails da rotina — crons da Vercel (vercel.json), horário de Fortaleza.

/api/daily  (PAUSADA desde 09/11/2026; era todo dia ~07:30) -> DAILY_TO: o que vence hoje, o que atrasou
            ontem e as entregas da semana, por projeto, nos setores
            Prospecção/Legalização/Novos Produtos.
/api/weekly (segunda ~18:00, rito da Sprint) -> WEEKLY_TO: placar das metas,
            entregas da semana e marcos do mês por projeto, riscos.

Dados: chaves dados_atividades / dados_marcos gravadas por api/importar.py a
cada export. Envio: SMTP Gmail com SMTP_USER/SMTP_PASSWORD (senha de app).
Teste sem enviar: GET /api/daily?dry=1&token=<IMPORT_TOKEN> (idem /api/weekly).
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
# Daily pausada pela Carol em 09/11/2026. Para religar: True aqui + cron
# {"path": "/api/daily", "schedule": "30 10 * * *"} de volta no vercel.json.
DAILY_ATIVA = False
DAILY_TO = os.environ.get("DAILY_TO", "desenvolvimentoimobole@vianaemoura.com.br")
WEEKLY_TO = os.environ.get(
    "WEEKLY_TO", "desenvolvimentoimobole@vianaemoura.com.br, filipecholanda@olecasas.com.br")
# Engenharia de Produto entrou em 09/11/2026 (está com o DI); Engenharia de Custo não.
FOCO = ("PROSP", "LEGAL", "NOVOS", "ENGENHARIA DE PRODUTO")
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
    # Engenharia do Caucaia fica de fora por enquanto (Carol, 09/11/2026)
    if "ENGENHARIA" in s and "CAUCAIA" in (x.get("projeto") or "").upper():
        return False
    return True


def setor_txt(s):
    s = (s or "").upper()
    k = next((k for k in NOME_SETOR if k in s), None)
    return NOME_SETOR[k] if k else s.title()


def grupo_de(x):
    """Nível entre o setor e a atividade (ex.: 'DVT de esgoto') — pedido da
    Carol em 09/11/2026 para localizar a atividade dentro do processo."""
    g = (x.get("grupo") or "").strip()
    return f" <span style='color:#64748b'>· {g}</span>" if g else ""


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
        return f"<li>{pref}{setor_txt(x['setor'])}{grupo_de(x)}: {x['atividade']}{pct}</li>"

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


COR_SETOR = {"PROSP": "#E8622A", "LEGAL": "#5B2D86", "NOVOS": "#1e5aa8",
             "ENGENHARIA DE PRODUTO": "#0f766e"}
NOME_SETOR = {"PROSP": "Prospecção", "LEGAL": "Legalização", "NOVOS": "Novos Produtos",
              "ENGENHARIA DE PRODUTO": "Eng. de Produto"}


def chip_setor(s):
    s = (s or "").upper()
    k = next((k for k in COR_SETOR if k in s), None)
    return ("<span style='background:%s;color:#fff;border-radius:10px;padding:1px 9px;"
            "font-size:11px;font-weight:600'>%s</span>"
            % (COR_SETOR.get(k, "#64748b"), NOME_SETOR.get(k, s.title())))


def monta_weekly(atv, marcos, hoje):
    """Weekly da Sprint (aprovada pela Carol em 09/11/2026): placar das metas,
    entregas da semana por projeto, marcos do mês e riscos."""
    hj = hoje.isoformat()
    dom = (hoje + timedelta(days=(6 - hoje.weekday()))).isoformat()
    prox = hoje.replace(day=28) + timedelta(days=4)
    fim_mes = (prox - timedelta(days=prox.day)).isoformat()
    meses = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
             "agosto", "setembro", "outubro", "novembro", "dezembro"]

    tudo = [x for x in sum(atv["atividades"].values(), []) if foco(x)]
    ms = [m for m in marcos["marcos"]
          if not any(f in (m.get("ugb") or "").upper() for f in FORA)
          and (m.get("projeto") or "") not in PROJ_FORA]
    pend = [m for m in ms if (m.get("pct") or 0) < 100]
    concluidos = len(ms) - len(pend)
    no_prazo = [m for m in pend if (m.get("desvio_dias") or 0) <= 0]
    em_desvio = [m for m in pend if (m.get("desvio_dias") or 0) > 0]
    vencidos = [m for m in pend if m.get("meta") and m["meta"] < hj]

    semana = [x for x in tudo if x.get("termino") and hj <= x["termino"] <= dom
              and (x.get("pct") or 0) < 100]
    atrasadas = [x for x in tudo if x.get("termino") and x["termino"] < hj
                 and (x.get("pct") or 0) < 100]
    sem_proj, atr_proj = {}, {}
    for x in semana:
        sem_proj.setdefault(x["projeto"], []).append(x)
    for x in atrasadas:
        atr_proj[x["projeto"]] = atr_proj.get(x["projeto"], 0) + 1
    marcos_mes = sorted([m for m in pend if (
        (m.get("meta") and hj <= m["meta"] <= fim_mes) or
        (m.get("termino_atual") and hj <= m["termino_atual"] <= fim_mes))],
        key=lambda z: z.get("meta") or z.get("termino_atual") or "9")

    H = ["<h2 style='color:#1D3461;border-bottom:3px solid #E8622A;padding-bottom:6px'>"
         "Weekly DI · Sprint da semana %s a %s</h2>" % (br(hj), br(dom))]

    H.append("<h3 style='color:#1D3461;margin:16px 0 6px'>🏆 Placar das metas (dia 0 = 14/09)</h3>"
             "<table style='border-collapse:collapse;width:100%;font-size:13.5px'><tr>")
    for n, rot, fundo, cor in ((concluidos, "concluídos", "#dcfce7", "#16a34a"),
                               (len(no_prazo), "no prazo", "#eff6ff", "#1e5aa8"),
                               (len(em_desvio), "em desvio", "#fef3c7", "#b45309"),
                               (len(vencidos), "meta vencida", "#fee2e2", "#dc2626")):
        H.append("<td style='padding:8px;background:%s;text-align:center'>"
                 "<b style='font-size:22px;color:%s'>%d</b><br>%s</td>" % (fundo, cor, n, rot))
    H.append("</tr></table>")

    H.append("<h3 style='color:#1D3461;margin:18px 0 6px'>🏃 Sprint da semana — %d entregas</h3>"
             % len(semana))
    if not sem_proj:
        H.append("<p>Sem entregas programadas para esta semana nos 3 setores.</p>")
    for proj in sorted(sem_proj, key=lambda p: (prioridade_projeto(p), p)):
        atr = atr_proj.get(proj, 0)
        badge = (" <span style='background:#fee2e2;color:#dc2626;border-radius:10px;"
                 "padding:1px 9px;font-size:11px;font-weight:700'>%d atrasada(s)</span>" % atr
                 if atr else "")
        H.append("<h4 style='background:#1D3461;color:#fff;padding:6px 12px;border-radius:6px;"
                 "margin:14px 0 4px;font-size:14px'>%s%s</h4><ul style='margin:4px 0 6px'>"
                 % (proj, badge))
        for x in sorted(sem_proj[proj], key=lambda z: z["termino"]):
            pct = " (%d%%)" % x["pct"] if x.get("pct") else ""
            H.append("<li style='margin:3px 0'><b>%s</b> · %s%s %s%s</li>"
                     % (br(x["termino"]), chip_setor(x["setor"]), grupo_de(x),
                        x["atividade"], pct))
        H.append("</ul>")

    H.append("<h3 style='color:#1D3461;margin:18px 0 6px'>🎯 Marcos de %s</h3>"
             % meses[hoje.month])
    if not marcos_mes:
        H.append("<p>Nenhum marco pendente para o resto do mês.</p>")
    mm_proj = {}
    for m in marcos_mes:
        mm_proj.setdefault(m["projeto"], []).append(m)
    for proj in sorted(mm_proj, key=lambda p: (prioridade_projeto(p), p)):
        H.append("<h4 style='background:#1D3461;color:#fff;padding:6px 12px;border-radius:6px;"
                 "margin:14px 0 4px;font-size:14px'>%s</h4><ul style='margin:4px 0 6px'>" % proj)
        for m in mm_proj[proj]:
            desv = m.get("desvio_dias") or 0
            H.append("<li style='margin:3px 0'>🎯 %s%s <b>%s</b> · meta <b>%s</b> · "
                     "término atual %s · %d%% · <b style='color:%s'>%s</b></li>"
                     % (chip_setor(m.get("setor")), grupo_de(m), m["marco"],
                        br(m.get("meta")), br(m.get("termino_atual")), m.get("pct") or 0,
                        "#dc2626" if desv > 0 else "#16a34a",
                        "+%dd vs meta" % desv if desv > 0 else "no prazo"))
        H.append("</ul>")

    if vencidos or atrasadas:
        H.append("<h3 style='color:#1D3461;margin:18px 0 6px'>⚠️ Riscos da sprint</h3><ul>")
        for m in sorted(vencidos, key=lambda z: z["meta"])[:6]:
            H.append("<li style='margin:3px 0'><b style='color:#dc2626'>%s</b> · %s — meta era "
                     "%s, término atual %s (%d%%)</li>"
                     % (m["marco"], m["projeto"], br(m["meta"]),
                        br(m.get("termino_atual")), m.get("pct") or 0))
        if atr_proj:
            H.append("<li style='margin:3px 0'>Atrasadas por projeto: " + " · ".join(
                "<b>%s</b> (%d)" % kv for kv in sorted(atr_proj.items(), key=lambda kv: -kv[1]))
                + "</li>")
        H.append("</ul>")

    H.append("<p style='margin-top:14px'><a href='https://painel-ole-vm.vercel.app/' "
             "style='color:#1D3461;font-weight:bold'>Abrir o painel →</a></p>")
    assunto = ("Weekly DI · sprint %s–%s — %d entregas · %d marcos no mês"
               % (br(hj), br(dom), len(semana), len(marcos_mes)))
    return assunto, "".join(H)


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
    MODO = "daily"      # api/weekly.py herda esta classe com MODO = "weekly"

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
            saida = {"hoje": hoje.isoformat(), "modo": self.MODO, "dry": dry, "envios": []}

            if self.MODO == "daily" and not DAILY_ATIVA:
                return self.responder(200, {"modo": "daily", "desativada": True, "envios": []})

            if self.MODO == "weekly":
                pares = [(WEEKLY_TO,) + monta_weekly(atv, marcos, hoje)]
            else:
                assunto, html, tem = monta_daily(atv, marcos, hoje)
                pares = [(DAILY_TO, assunto, html)] if tem else []

            for para, assunto, html in pares:
                if dry:
                    saida["envios"].append({"para": para, "assunto": assunto})
                else:
                    ok, info = enviar(para, assunto, html)
                    saida["envios"].append({"para": para, "assunto": assunto,
                                            "ok": ok, "info": info})

            self.responder(200, saida)
        except Exception as e:
            self.responder(500, {"erro": str(e), "trace": traceback.format_exc()[-1000:]})
