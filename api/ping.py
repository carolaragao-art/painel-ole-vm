# Teste: a Vercel roda Python neste projeto Next.js?
from http.server import BaseHTTPRequestHandler
import json, sys

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            import openpyxl
            ver = openpyxl.__version__
        except Exception as e:
            ver = "sem openpyxl: %s" % e
        corpo = json.dumps({
            "ok": True,
            "python": sys.version.split()[0],
            "openpyxl": ver,
        }).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(corpo)
