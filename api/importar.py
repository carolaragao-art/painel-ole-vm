# -*- coding: utf-8 -*-
"""Recebe o Excel do Smartsheet e refaz as páginas do painel — no servidor.

Antes, essa etapa rodava no notebook da Carol (tarefa agendada do Windows).
Agora o Apps Script, que já salva o anexo no Drive, manda o mesmo arquivo para cá:

    POST /api/importar?token=<IMPORT_TOKEN>    corpo = bytes do .xlsx

A função recria em /tmp a mesma árvore de pastas que os scripts esperam, roda
parse_excel + build_marcos + build_projetos sem alterá-los, e grava o resultado
no Postgres (kv_state). As páginas são servidas de lá por /api/pagina.

Nada é gravado no repositório: dado é dado, código é código.
"""
from http.server import BaseHTTPRequestHandler
import importlib
import io
import json
import os
import shutil
import sys
import traceback
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.abspath(__file__))
ORIGEM = os.path.join(RAIZ, "rotina")

# espelha a árvore do Drive, porque os scripts se localizam por caminho relativo
BASE = "/tmp/olevm"
DIR_GESTAO = os.path.join(BASE, "00 Gestao do Setor", "Ole VM Gestao")
DIR_ROTINA = os.path.join(DIR_GESTAO, "rotina-smartsheet")
DIR_XLSX = os.path.join(BASE, "00 Gestao do Setor", "06 Smartsheet")

TABELA = "rotina_painel"      # separada do kv_state de propósito (ver ler_chave)

CHAVE_MARCOS = "pagina_marcos"
CHAVE_PROJETOS = "pagina_projetos"
CHAVE_BASELINE = "marcos_baseline"
CHAVE_STATUS = "rotina_status"


# ---------------------------------------------------------------- banco
def conectar():
    import pg8000.dbapi
    from urllib.parse import urlparse, unquote

    url = (os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
           or os.environ.get("POSTGRES_URL_NON_POOLING") or "")
    if not url:
        raise RuntimeError("Sem DATABASE_URL/POSTGRES_URL no ambiente.")
    u = urlparse(url)
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return pg8000.dbapi.connect(
        user=unquote(u.username or ""), password=unquote(u.password or ""),
        host=u.hostname, port=u.port or 5432,
        database=(u.path or "/").lstrip("/").split("?")[0], ssl_context=ctx,
    )


def preparar_tabela(cur):
    """Tabela só da rotina. O kv_state não serve: a página inicial injeta TODAS as
    chaves dele dentro de uma tag <script>, e um HTML com </script> ali quebra o
    painel inteiro (aconteceu em 29/10/2026)."""
    cur.execute(
        "CREATE TABLE IF NOT EXISTS %s ("
        "  k text PRIMARY KEY,"
        "  v text,"
        "  updated_at timestamptz DEFAULT now())" % TABELA
    )
    # migração automática do que já estava no kv_state
    for k in (CHAVE_BASELINE, "import_token"):
        cur.execute("SELECT v FROM %s WHERE k = %%s" % TABELA, (k,))
        if cur.fetchone():
            continue
        cur.execute("SELECT v FROM kv_state WHERE k = %s", (k,))
        linha = cur.fetchone()
        if linha and linha[0]:
            gravar_chave(cur, k, linha[0])


def ler_chave(cur, k):
    cur.execute("SELECT v FROM %s WHERE k = %%s" % TABELA, (k,))
    linha = cur.fetchone()
    if linha:
        return linha[0]
    cur.execute("SELECT v FROM kv_state WHERE k = %s", (k,))   # reserva
    linha = cur.fetchone()
    return linha[0] if linha else None


def gravar_chave(cur, k, v):
    cur.execute(
        "INSERT INTO %s (k, v, updated_at) VALUES (%%s, %%s, now()) "
        "ON CONFLICT (k) DO UPDATE SET v = EXCLUDED.v, updated_at = now()" % TABELA,
        (k, v),
    )


# ---------------------------------------------------------------- rotina
def preparar_arvore(xlsx_bytes, baseline_txt):
    if os.path.isdir(BASE):
        shutil.rmtree(BASE, ignore_errors=True)
    os.makedirs(DIR_ROTINA, exist_ok=True)
    os.makedirs(DIR_XLSX, exist_ok=True)

    for nome in os.listdir(ORIGEM):
        if os.path.isdir(os.path.join(ORIGEM, nome)):
            continue                       # ignora __pycache__ e afins
        if nome == "logo-olevm.png":
            shutil.copy(os.path.join(ORIGEM, nome), os.path.join(DIR_GESTAO, nome))
        else:
            shutil.copy(os.path.join(ORIGEM, nome), os.path.join(DIR_ROTINA, nome))

    with open(os.path.join(DIR_XLSX, "OLE VM - DEV IMOB_AUTO.xlsx"), "wb") as fh:
        fh.write(xlsx_bytes)

    # o baseline das metas é add-only e mora no banco: sem ele, toda meta vira "nova"
    if baseline_txt:
        with io.open(os.path.join(DIR_ROTINA, "marcos_baseline.json"), "w",
                     encoding="utf-8") as fh:
            fh.write(baseline_txt)


def rodar(nome_modulo, chamar_main=False):
    """Importa o script do zero (o código de topo precisa rodar a cada chamada)."""
    for m in list(sys.modules):
        if m in ("parse_excel", "build_marcos", "build_projetos", "projetos_cond"):
            del sys.modules[m]
    importlib.invalidate_caches()
    mod = importlib.import_module(nome_modulo)
    if chamar_main and hasattr(mod, "main"):
        mod.main()
    return mod


def processar(xlsx_bytes):
    saida = io.StringIO()
    antigo_stdout, antigo_argv, antigo_path = sys.stdout, sys.argv, list(sys.path)
    sys.stdout = saida
    sys.argv = ["parse_excel.py"]
    sys.path.insert(0, DIR_ROTINA)
    try:
        rodar("parse_excel", chamar_main=True)
        rodar("build_marcos")                      # gera no import
        rodar("build_projetos", chamar_main=True)
    finally:
        sys.stdout, sys.argv, sys.path = antigo_stdout, antigo_argv, antigo_path

    def ler(nome):
        with io.open(os.path.join(DIR_ROTINA, nome), encoding="utf-8") as fh:
            return fh.read()

    return {
        "marcos_html": ler("marcos.html"),
        "projetos_html": ler("projetos.html"),
        "baseline": ler("marcos_baseline.json"),
        "marcos_json": ler("marcos.json"),
        "log": saida.getvalue(),
    }


# ---------------------------------------------------------------- handler
class handler(BaseHTTPRequestHandler):
    def responder(self, codigo, dados):
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        self.responder(200, {"ok": True, "uso": "POST com o .xlsx no corpo e ?token="})

    def do_POST(self):
        try:
            enviado = ""
            if "?" in self.path:
                from urllib.parse import parse_qs
                enviado = (parse_qs(self.path.split("?", 1)[1]).get("token") or [""])[0]
            enviado = enviado or self.headers.get("x-token", "")

            con = conectar()
            cur = con.cursor()
            preparar_tabela(cur)
            con.commit()
            # o segredo vive no banco (chave import_token); a variável de ambiente
            # continua valendo, se um dia for configurada na Vercel.
            esperado = os.environ.get("IMPORT_TOKEN", "") or (ler_chave(cur, "import_token") or "")
            if not esperado or not enviado or enviado != esperado:
                cur.close()
                con.close()
                return self.responder(401, {"erro": "token invalido"})

            tamanho = int(self.headers.get("Content-Length") or 0)
            if tamanho < 5000:
                return self.responder(400, {"erro": "corpo vazio ou pequeno demais"})
            bruto = self.rfile.read(tamanho)
            if bruto[:2] != b"PK":
                cur.close()
                con.close()
                return self.responder(400, {"erro": "o corpo nao parece um .xlsx"})

            baseline = ler_chave(cur, CHAVE_BASELINE)
            # trava de segurança: sem baseline, o parse registraria a data de hoje
            # como meta de todos os marcos e apagaria o histórico de desvio.
            if not baseline:
                cur.close()
                con.close()
                return self.responder(409, {
                    "erro": "baseline das metas ausente no banco",
                    "detalhe": "grave a chave marcos_baseline antes de importar",
                })

            preparar_arvore(bruto, baseline)
            r = processar(bruto)

            gravar_chave(cur, CHAVE_MARCOS, r["marcos_html"])
            gravar_chave(cur, CHAVE_PROJETOS, r["projetos_html"])
            gravar_chave(cur, CHAVE_BASELINE, r["baseline"])
            marcos = json.loads(r["marcos_json"])
            status = {
                "em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "marcos": len(marcos.get("marcos", [])),
                "gerado_em": marcos.get("gerado_em"),
                "bytes_xlsx": len(bruto),
                "log": r["log"][-800:],
            }
            gravar_chave(cur, CHAVE_STATUS, json.dumps(status, ensure_ascii=False))
            con.commit()
            cur.close()
            con.close()

            self.responder(200, {"ok": True, **{k: v for k, v in status.items() if k != "log"}})
        except Exception as e:
            self.responder(500, {"erro": str(e), "trace": traceback.format_exc()[-1200:]})
