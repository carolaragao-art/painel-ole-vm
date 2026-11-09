# -*- coding: utf-8 -*-
"""Gestao a vista — rodada da semana ligada aos marcos do mes.

Pedido do gestor da Carol (09/11/2026): deixar visivel a entrega da semana
que puxa o marco do mes. Le atividades.json + marcos.json (gerados pelo
parse_excel) e escreve semana.html no mesmo estilo do painel.
Roda no notebook (run_rotina) e no servidor (/api/importar), sem argumentos.
"""
import io
import json
import os
from collections import defaultdict
from datetime import date, timedelta

AQUI = os.path.dirname(os.path.abspath(__file__))

FOCO = ("PROSP", "LEGAL", "NOVOS")
FORA = ("MACROFLUXO",)
PROJ_FORA = ("PS4 - T+1",)

COR = {"PROSP": "#E8622A", "LEGAL": "#5B2D86", "NOVOS": "#1e5aa8"}
NOME = {"PROSP": "Prospecção", "LEGAL": "Legalização", "NOVOS": "Novos Produtos"}


def br(s):
    return "%s/%s" % (s[8:10], s[5:7]) if s else "—"


def setor_key(s):
    s = (s or "").upper()
    for k in COR:
        if k in s:
            return k
    return None


def foco(x):
    if setor_key(x.get("setor")) is None:
        return False
    if any(f in (x.get("ugb") or "").upper() for f in FORA):
        return False
    if (x.get("projeto") or "") in PROJ_FORA:
        return False
    return True


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


def chip_setor(s):
    k = setor_key(s)
    c = COR.get(k, "#64748b")
    n = NOME.get(k, (s or "").title())
    return ("<span style='background:%s;color:#fff;border-radius:10px;"
            "padding:1px 9px;font-size:11px;font-weight:600'>%s</span>" % (c, n))


def main():
    atv = json.load(io.open(os.path.join(AQUI, "atividades.json"), encoding="utf-8"))
    marcos = json.load(io.open(os.path.join(AQUI, "marcos.json"), encoding="utf-8"))

    hoje = date(*[int(n) for n in atv["hoje"].split("-")])
    hj = hoje.isoformat()
    dom = (hoje + timedelta(days=(6 - hoje.weekday()))).isoformat()
    mes_ini = hoje.replace(day=1).isoformat()
    if hoje.month == 12:
        fim_mes = hoje.replace(day=31).isoformat()
    else:
        fim_mes = (hoje.replace(day=1, month=hoje.month + 1) - timedelta(days=1)).isoformat()
    MESES = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
             "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    nome_mes = "%s %d" % (MESES[hoje.month], hoje.year)

    tudo = [x for x in sum(atv["atividades"].values(), []) if foco(x)]
    ms = [m for m in marcos["marcos"]
          if not any(f in (m.get("ugb") or "").upper() for f in FORA)
          and (m.get("projeto") or "") not in PROJ_FORA]

    pend = lambda z: (z.get("pct") or 0) < 100
    marcos_mes = [m for m in ms if pend(m) and (
        (m.get("meta") and mes_ini <= m["meta"] <= fim_mes) or
        (m.get("termino_atual") and mes_ini <= m["termino_atual"] <= fim_mes))]
    marcos_vencidos = [m for m in ms if pend(m) and m.get("meta")
                       and m["meta"] < mes_ini and m not in marcos_mes]

    semana = [x for x in tudo if pend(x) and x.get("termino") and hj <= x["termino"] <= dom]
    resto = [x for x in tudo if pend(x) and x.get("termino") and dom < x["termino"] <= fim_mes]
    atrasadas = [x for x in tudo if pend(x) and x.get("termino") and x["termino"] < hj]
    hoje_n = sum(1 for x in semana if x["termino"] == hj)

    sem_proj = defaultdict(list)
    for x in semana:
        sem_proj[x["projeto"]].append(x)
    resto_proj = defaultdict(list)
    for x in resto:
        resto_proj[x["projeto"]].append(x)
    atr_proj = defaultdict(int)
    for x in atrasadas:
        atr_proj[x["projeto"]] += 1

    def card_marco(m):
        desv = m.get("desvio_dias") or 0
        if desv > 0:
            tag = "<span style='color:#dc2626;font-weight:700'>+%dd vs meta</span>" % desv
        elif desv < 0:
            tag = "<span style='color:#16a34a;font-weight:700'>%dd vs meta</span>" % desv
        else:
            tag = "<span style='color:#16a34a;font-weight:700'>na meta</span>"
        estrela = "★ " if "CONDOMÍNIO MORADA" in (m.get("projeto") or "").upper() else ""
        return ("<div class='marco' style='border-left-color:%s'>"
                "<div class='mnome'>%s%s</div>"
                "<div class='minfo'>%s &nbsp;·&nbsp; meta <b>%s</b> &nbsp;·&nbsp; "
                "término atual <b>%s</b> &nbsp;·&nbsp; %d%% &nbsp;·&nbsp; %s</div></div>"
                % (COR.get(setor_key(m.get("setor")), "#64748b"), estrela, m["marco"],
                   m["projeto"], br(m.get("meta")), br(m.get("termino_atual")),
                   m.get("pct") or 0, tag))

    H = []
    H.append("""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gestão à Vista — Semana</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
 body{font-family:Poppins,Arial,sans-serif;background:#f1f5f9;color:#1e293b;margin:0}
 .wrap{max-width:900px;margin:0 auto;padding:16px}
 h2.sec{color:#1D3461;border-bottom:3px solid #E8622A;padding-bottom:6px;margin:28px 0 10px;font-size:20px}
 .kpis{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}
 .kpi{flex:1;min-width:140px;background:#fff;border-radius:10px;padding:12px 14px;border:1px solid #e2e8f0}
 .kpi b{font-size:26px;color:#1D3461;display:block}
 .kpi span{font-size:12px;color:#64748b}
 .marco{border:1px solid #e2e8f0;border-left:5px solid #64748b;border-radius:8px;
        padding:9px 12px;margin:6px 0;background:#fff}
 .mnome{font-weight:700;color:#1D3461}
 .minfo{font-size:12.5px;color:#475569;margin-top:2px}
 h3.proj{background:#1D3461;color:#fff;padding:7px 12px;border-radius:6px;margin:18px 0 6px;font-size:15px}
 ul{margin:4px 0 8px;padding-left:22px} li{margin:3px 0;font-size:13.5px}
 .badge{background:#fee2e2;color:#dc2626;border-radius:10px;padding:1px 9px;font-size:11px;font-weight:700}
 header{background:#1D3461;color:#fff;padding:22px 16px;text-align:center}
 html.embed header{display:none}
 .nota{font-size:12.5px;color:#64748b;margin-top:10px}
 footer{text-align:center;color:#94a3b8;font-size:11px;margin:26px 0}
</style>
<script>if(window.self!==window.top)document.documentElement.classList.add('embed')</script>
</head><body><header>
 <div style="font-size:12px;letter-spacing:2px;color:#E8A020;font-weight:600">OLÉ V&amp;M · DESENVOLVIMENTO IMOBILIÁRIO</div>
 <div style="font-size:26px;font-weight:800;margin-top:4px">Gestão à Vista — Semana</div>
</header><div class="wrap">""")

    H.append("<p style='text-align:center;color:#475569;font-size:13px;margin:12px 0 0'>"
             "Semana de <b>%s</b> a <b>%s</b> · mês de referência <b>%s</b> · "
             "Prospecção · Legalização · Novos Produtos</p>" % (br(hj), br(dom), nome_mes))

    H.append("<div class='kpis'>"
             "<div class='kpi'><b style='color:#E8622A'>%d</b><span>para hoje</span></div>"
             "<div class='kpi'><b>%d</b><span>entregas na semana</span></div>"
             "<div class='kpi'><b>%d</b><span>marcos no mês</span></div>"
             "<div class='kpi'><b style='color:#dc2626'>%d</b><span>atrasadas</span></div>"
             "</div>" % (hoje_n, len(semana), len(marcos_mes), len(atrasadas)))

    H.append("<h2 class='sec'>🎯 Marcos de %s — aonde a semana leva</h2>" % MESES[hoje.month].lower())
    if not marcos_mes:
        H.append("<p>Nenhum marco com meta ou término neste mês.</p>")
    for k in ("PROSP", "LEGAL", "NOVOS"):
        grupo = sorted([m for m in marcos_mes if setor_key(m.get("setor")) == k],
                       key=lambda z: z.get("meta") or z.get("termino_atual") or "9")
        if not grupo:
            continue
        H.append("<div style='margin:14px 0 4px'>%s</div>" % chip_setor(k))
        H.extend(card_marco(m) for m in grupo)
    if marcos_vencidos:
        H.append("<p class='nota'><b style='color:#dc2626'>%d marco(s) com meta vencida</b> "
                 "antes do mês seguem pendentes — pauta do replanejamento de segunda.</p>"
                 % len(marcos_vencidos))

    H.append("<h2 class='sec'>🏃 Rodada da semana por projeto</h2>")
    if not sem_proj:
        H.append("<p>Sem entregas programadas para esta semana.</p>")
    for proj in sorted(sem_proj, key=lambda p: (prioridade_projeto(p), p)):
        atr = atr_proj.get(proj, 0)
        badge = " <span class='badge'>%d atrasada(s)</span>" % atr if atr else ""
        H.append("<h3 class='proj'>%s%s</h3><ul>" % (proj, badge))
        for x in sorted(sem_proj[proj], key=lambda z: z["termino"]):
            pct = " (%d%%)" % x["pct"] if x.get("pct") else ""
            dia = ("<b style='color:#E8622A'>HOJE</b>" if x["termino"] == hj
                   else "<b>%s</b>" % br(x["termino"]))
            H.append("<li>%s · %s %s%s</li>" % (dia, chip_setor(x["setor"]), x["atividade"], pct))
        H.append("</ul>")

    H.append("<h2 class='sec'>📦 Resto do mês</h2>")
    if not resto_proj:
        H.append("<p>Nada mais programado até o fim do mês.</p>")
    for proj in sorted(resto_proj, key=lambda p: (prioridade_projeto(p), p)):
        H.append("<h3 class='proj'>%s</h3><ul>" % proj)
        for x in sorted(resto_proj[proj], key=lambda z: z["termino"]):
            pct = " (%d%%)" % x["pct"] if x.get("pct") else ""
            H.append("<li><b>%s</b> · %s %s%s</li>"
                     % (br(x["termino"]), chip_setor(x["setor"]), x["atividade"], pct))
        H.append("</ul>")

    so_atraso = [p for p in atr_proj if p not in sem_proj and p not in resto_proj]
    if so_atraso:
        H.append("<p class='nota'>Só com pendências atrasadas (sem entrega nova no mês): "
                 + ", ".join("<b>%s</b> (%d)" % (p, atr_proj[p]) for p in sorted(so_atraso))
                 + "</p>")

    H.append("<footer>atualizado em %s · gerado automaticamente pela rotina</footer>"
             "</div></body></html>" % hoje.strftime("%d/%m/%Y"))

    with io.open(os.path.join(AQUI, "semana.html"), "w", encoding="utf-8") as fh:
        fh.write("".join(H))
    print("semana.html: %d na semana, %d marcos no mes, %d atrasadas"
          % (len(semana), len(marcos_mes), len(atrasadas)))


main()
