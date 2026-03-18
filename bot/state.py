from datetime import datetime
from .config import get_capital_total

ESTADO_GLOBAL = {
    "status": "iniciando",
    "bot_ativo": True,
    "capital": get_capital_total(),
    "capital_inicial": get_capital_total(),
    "trades": 0,
    "wins": 0,
    "losses": 0,
    "lucro_total": 0.0,
    "posicoes": {},
    "sentimento": 50,
    "fear_greed_label": "Neutro",
    "whale_alertas": [],
    "nlp_score": 0,
    "nlp_label": "Neutro",
    "news_score": 0.0,
    "news_label": "Neutro",
    "news_items": [],
    "ultimo_sinal": {},
    "historico_pnl": [],
    "parametros": {},
    "ultima_otimizacao": "Nunca",
    "log_recente": [],
    "inicio": datetime.now().isoformat(),
    "pares_ativos": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
}

SESSIONS = set()
