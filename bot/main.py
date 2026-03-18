from collections import deque
import threading
from .dashboard import iniciar_dashboard
from .engine import run_engine
from .logging_setup import log, LogCapturador

def main():
    log.info("╔══════════════════════════════════════════════════════╗")
    log.info("║          BOT ULTRA v4.0 - FORA DA CURVA             ║")
    log.info("║     Estrutura profissional + Alpha Vantage          ║")
    log.info("╚══════════════════════════════════════════════════════╝")

    log_buffer = deque(maxlen=100)
    handler = LogCapturador(log_buffer)
    handler.setFormatter(__import__("logging").Formatter("%(asctime)s %(message)s", "%Y-%m-%d %H:%M:%S"))
    __import__("logging").getLogger("bot_ultra").addHandler(handler)

    threading.Thread(target=iniciar_dashboard, daemon=True).start()
    run_engine(log_buffer)
