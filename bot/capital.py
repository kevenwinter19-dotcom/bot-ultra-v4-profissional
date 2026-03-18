import numpy as np
from collections import deque
from .config import RISCO_BASE, MAX_DRAWDOWN

class GestaoCapital:
    def __init__(self, capital):
        self.capital = capital
        self.pico = capital
        self.historico_retornos = deque(maxlen=50)

    def kelly(self):
        if len(self.historico_retornos) < 10:
            return RISCO_BASE
        r = list(self.historico_retornos)
        wins = [x for x in r if x > 0]
        losses = [x for x in r if x < 0]
        if not wins or not losses:
            return RISCO_BASE
        p = len(wins) / len(r)
        q = 1 - p
        b = np.mean(wins) / abs(np.mean(losses))
        k = (b * p - q) / b
        return max(0.005, min(k * 0.5, 0.04))

    def tamanho(self, preco, stop):
        k = self.kelly()
        risco_usd = self.capital * k
        pct_sl = abs(preco - stop) / preco
        if pct_sl == 0:
            return 0, 0
        val = min(risco_usd / pct_sl, self.capital * 0.25)
        return val, round(val / preco, 6)

    def atualizar(self, novo):
        self.capital = novo
        if novo > self.pico:
            self.pico = novo

    def drawdown(self):
        return (self.pico - self.capital) / self.pico if self.pico else 0

    def pode_operar(self):
        return self.drawdown() < MAX_DRAWDOWN
