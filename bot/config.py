import json
import os
from pathlib import Path
from threading import RLock

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
TEMPLATES_DIR = BASE_DIR / "templates"

SECRETS_PATH = BASE_DIR / "secrets.json"
MEMORY_PATH = DATA_DIR / "memoria_v4.json"

DEFAULT_SECRETS = {
    "binance_api_key": "",
    "binance_api_secret": "",
    "usar_testnet": True,
    "capital_total": 100.0,
    "alpha_vantage_api_key": "J6VXYQ18BS5EXNCO",
    "port": 8080,
    "panel_password": "admin123",
}

SECRETS_LOCK = RLock()
STATE_LOCK = RLock()
SESSION_LOCK = RLock()

def load_secrets() -> dict:
    if not SECRETS_PATH.exists():
        save_secrets(DEFAULT_SECRETS.copy())
        return DEFAULT_SECRETS.copy()
    with SECRETS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)
    merged = DEFAULT_SECRETS.copy()
    merged.update(data)
    return merged

def save_secrets(data: dict) -> None:
    with SECRETS_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

SECRETS = load_secrets()

PARES_PADRAO = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"]
RISCO_BASE = 0.02
MAX_POSICOES = 2
MAX_DRAWDOWN = 0.15
INTERVALO = 60

def get_port() -> int:
    return int(SECRETS.get("port", 8080))

def get_capital_total() -> float:
    return float(SECRETS.get("capital_total", 100.0))

def get_testnet() -> bool:
    return bool(SECRETS.get("usar_testnet", True))
