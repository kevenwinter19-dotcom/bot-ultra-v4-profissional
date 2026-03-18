from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json
import hmac

from .config import TEMPLATES_DIR, STATE_LOCK, SECRETS_LOCK, SECRETS, save_secrets, get_port
from .state import ESTADO_GLOBAL
from .logging_setup import log

DASHBOARD_FILE = TEMPLATES_DIR / "dashboard_admin.html"

def secure_compare(a: str, b: str) -> bool:
    return hmac.compare_digest((a or "").encode(), (b or "").encode())

class DashboardHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()
        self.close_connection = True

    def _send_html(self, html, code=200):
        body = html.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()
        self.close_connection = True

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if not length:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/estado":
            with STATE_LOCK:
                self._send_json(ESTADO_GLOBAL)
            return

        if self.path == "/api/news":
            with STATE_LOCK:
                self._send_json({
                    "items": ESTADO_GLOBAL.get("news_items", []),
                    "score": ESTADO_GLOBAL.get("news_score", 0),
                    "label": ESTADO_GLOBAL.get("news_label", "Neutro"),
                })
            return

        try:
            html = DASHBOARD_FILE.read_text(encoding="utf-8")
        except FileNotFoundError:
            html = "<h1>dashboard_admin.html não encontrado</h1>"

        with SECRETS_LOCK:
            alpha_key = SECRETS.get("alpha_vantage_api_key", "")
        html = html.replace("__DEFAULT_ALPHA_KEY__", alpha_key)
        self._send_html(html)

    def do_POST(self):
        try:
            body = self._read_json()
        except Exception as e:
            self._send_json({"ok": False, "erro": f"JSON inválido: {e}"}, 400)
            return

        if self.path == "/api/bot-control":
            ativo = bool(body.get("ativo", True))
            with STATE_LOCK:
                ESTADO_GLOBAL["bot_ativo"] = ativo
            log.info("Bot %s pelo painel", "LIGADO" if ativo else "DESLIGADO")
            self._send_json({"ok": True})
            return

        if self.path == "/api/pares":
            pares = body.get("pares", [])
            if isinstance(pares, list):
                with STATE_LOCK:
                    ESTADO_GLOBAL["pares_ativos"] = pares
                log.info("Pares atualizados: %s", pares)
            self._send_json({"ok": True})
            return

        if self.path == "/api/config":
            with SECRETS_LOCK:
                if "binance_key" in body:
                    SECRETS["binance_api_key"] = body.get("binance_key", "")
                    SECRETS["binance_api_secret"] = body.get("binance_secret", "")
                    SECRETS["usar_testnet"] = bool(body.get("testnet", True))
                    log.info("Binance API atualizada pelo painel")
                if "capital" in body:
                    try:
                        SECRETS["capital_total"] = float(body["capital"])
                    except Exception:
                        pass
                if "alpha_key" in body:
                    SECRETS["alpha_vantage_api_key"] = body.get("alpha_key", "")
                    log.info("Alpha Vantage atualizada pelo painel")
                save_secrets(SECRETS)
            self._send_json({"ok": True})
            return

        if self.path == "/api/analisar-noticia":
            titulo = str(body.get("titulo", ""))
            pos = ["bull", "rally", "surge", "gain", "alta", "compra", "subiu", "recorde", "approve", "etf"]
            neg = ["bear", "crash", "ban", "hack", "queda", "venda", "caiu", "perda", "fraud", "lawsuit"]
            t = titulo.lower()
            score = sum(1 for w in pos if w in t) - sum(1 for w in neg if w in t)
            if score > 0:
                analise = "Notícia positiva. Pressão compradora provável em BTC/ETH. Use como reforço de COMPRA, não como gatilho único."
            elif score < 0:
                analise = "Notícia negativa. Monitore suportes. Use como filtro para reduzir confiança em compras ou priorizar AGUARDAR."
            else:
                analise = "Notícia neutra. Aguarde confirmação dos indicadores técnicos."
            self._send_json({"analise": analise})
            return

        if self.path == "/api/reset":
            self._send_json({"ok": True})
            return

        self._send_json({"erro": "Endpoint nao encontrado"}, 404)

    def log_message(self, *args):
        return

def iniciar_dashboard():
    port = get_port()
    server = ThreadingHTTPServer(("0.0.0.0", port), DashboardHandler)
    log.info("🌐 Dashboard rodando na porta %s", port)
    server.serve_forever()
