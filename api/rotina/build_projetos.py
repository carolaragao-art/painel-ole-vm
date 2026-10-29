# -*- coding: utf-8 -*-
"""Gera projetos.html — aba "Projetos · Condomínio" do painel-ole-vm.

Cronograma (etapa + data planejada) vem do export do Smartsheet.
Empresa, projetista e pagamento vêm de depara_projetos.json (migrados uma
única vez da planilha manual "Lista Projetos.xlsx").
"""
import base64
import glob
import io
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from projetos_cond import extrair, chave, ETAPAS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PASTA_XLSX = os.path.normpath(os.path.join(HERE, "..", "..", "06 Smartsheet"))
LOGO = os.path.normpath(os.path.join(HERE, "..", "logo-olevm.png"))
AVISO_DIAS = 5          # regra combinada com a Carol


def dados():
    xlsx = max(glob.glob(os.path.join(PASTA_XLSX, "*DEV IMOB*.xlsx")), key=os.path.getmtime)
    projs, avisos, rollup = extrair(xlsx)
    try:
        dp = json.load(io.open(os.path.join(HERE, "depara_projetos.json"), encoding="utf-8"))
    except Exception:
        dp = {}
    orfaos = []
    for p in projs:
        c = chave(" > ".join(p["caminho"]))
        g = chave(p["grupo"])
        k = c[len(g) + 3:] if c.startswith(g) else c
        m = dp.get(k)
        if m:
            p.update({"apelido": m["apelido"], "empresa": m["empresa"],
                      "projetista": m["projetista"], "pagamento": m["pagamento"],
                      "obs": m["obs"]})
        else:
            orfaos.append(p["nome"])
            p.update({"apelido": p["nome"], "empresa": "", "projetista": "",
                      "pagamento": "", "obs": ""})
        p["grupo_curto"] = (p["grupo"].replace("PROJETOS ", "").replace("-", " ")
                            .title().replace("Nao Incidentes", "Não Incidentes"))
        p["caminho_txt"] = " › ".join(p["caminho"][1:-1])
    return (projs, avisos, orfaos, rollup, os.path.basename(xlsx),
            datetime.fromtimestamp(os.path.getmtime(xlsx)).strftime("%d/%m/%Y"))


TEMPLATE = io.open(os.path.join(HERE, "template_projetos.html"), encoding="utf-8").read()


def main():
    projs, avisos, orfaos, rollup, arq, quando = dados()
    logo = base64.b64encode(open(LOGO, "rb").read()).decode()
    html = (TEMPLATE
            .replace("__LOGO__", logo)
            .replace("__ETAPAS__", json.dumps(ETAPAS, ensure_ascii=False))
            .replace("__DADOS__", json.dumps(projs, ensure_ascii=False))
            .replace("__AVISOS__", json.dumps({"atipicos": avisos, "orfaos": orfaos}, ensure_ascii=False))
            .replace("__AVISO_DIAS__", str(AVISO_DIAS))
            .replace("__ROLLUP__", json.dumps(rollup, ensure_ascii=False))
            .replace("__FONTE__", arq)
            .replace("__QUANDO__", quando))
    dest = os.path.join(HERE, "projetos.html")
    io.open(dest, "w", encoding="utf-8", newline="").write(html)
    print("Projetos:", len(projs), "| sem de-para:", len(orfaos), "| export:", arq)
    print("Gerado:", dest, os.path.getsize(dest), "bytes")


if __name__ == "__main__":
    main()
