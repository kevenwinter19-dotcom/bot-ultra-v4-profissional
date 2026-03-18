import json
import numpy as np
from collections import deque
from .config import MEMORY_PATH
from .logging_setup import log

class AgenteQL:
    ACOES = ["AGUARDAR", "COMPRAR", "VENDER"]

    def __init__(self):
        self.alpha = 0.1
        self.gamma = 0.9
        self.epsilon = 0.2
        self.epsilon_min = 0.03
        self.epsilon_decay = 0.998
        self.q_table = {}
        self.historico = deque(maxlen=500)
        self.total_trades = 0
        self.lucro_total = 0.0
        self.wins = 0
        self.losses = 0
        self.carregar_memoria()

    def _get_q(self, e):
        if e not in self.q_table:
            self.q_table[e] = [0.0, 0.0, 0.0]
        return self.q_table[e]

    def codificar_estado(self, score_mtf, sentimento, nlp_score, whale_ratio):
        s_zona = "FORTE+" if score_mtf >= 7 else ("+" if score_mtf >= 4 else ("FORTE-" if score_mtf <= -7 else ("-" if score_mtf <= -4 else "N")))
        fg_zona = "ME" if sentimento <= 25 else ("M" if sentimento <= 45 else ("N" if sentimento <= 55 else ("G" if sentimento <= 75 else "GE")))
        nlp_z = "+" if nlp_score >= 3 else ("-" if nlp_score <= -3 else "N")
        wh_z = "W" if whale_ratio >= 3 else "n"
        rec = "".join("W" if r > 0 else "L" for r in list(self.historico)[-3:]).ljust(3, "N")
        return f"{s_zona}|{fg_zona}|{nlp_z}|{wh_z}|{rec}"

    def escolher_acao(self, estado, sinal_sistema):
        if np.random.rand() < self.epsilon:
            probs = [0.2, 0.6, 0.2] if sinal_sistema == "COMPRAR" else ([0.2, 0.2, 0.6] if sinal_sistema == "VENDER" else [0.6, 0.2, 0.2])
            return np.random.choice(3, p=probs)
        return int(np.argmax(self._get_q(estado)))

    def aprender(self, e, a, r, e2):
        q = self._get_q(e)
        qf = self._get_q(e2)
        q[a] += self.alpha * (r + self.gamma * max(qf) - q[a])
        self.q_table[e] = q
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    def registrar(self, lucro, capital):
        self.historico.append(lucro)
        self.total_trades += 1
        self.lucro_total += lucro
        if lucro > 0:
            self.wins += 1
        else:
            self.losses += 1
        self.salvar_memoria()
        log.info("📊 %s $%+.4f | Capital: $%.2f", "✅" if lucro > 0 else "❌", lucro, capital)

    def salvar_memoria(self):
        with open(MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump({
                "q_table": self.q_table,
                "epsilon": self.epsilon,
                "historico": list(self.historico),
                "total_trades": self.total_trades,
                "lucro_total": self.lucro_total,
                "wins": self.wins,
                "losses": self.losses,
            }, f, indent=2, ensure_ascii=False)

    def carregar_memoria(self):
        try:
            with open(MEMORY_PATH, "r", encoding="utf-8") as f:
                d = json.load(f)
            self.q_table = d.get("q_table", {})
            self.epsilon = d.get("epsilon", 0.2)
            self.historico = deque(d.get("historico", []), maxlen=500)
            self.total_trades = d.get("total_trades", 0)
            self.lucro_total = d.get("lucro_total", 0.0)
            self.wins = d.get("wins", 0)
            self.losses = d.get("losses", 0)
            log.info("🧠 Memória carregada: %s estados | %s trades", len(self.q_table), self.total_trades)
        except FileNotFoundError:
            log.info("🆕 Iniciando sem memória anterior.")
