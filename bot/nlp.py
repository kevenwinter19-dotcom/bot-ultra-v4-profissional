from datetime import datetime
import requests
from .logging_setup import log

class AnalisadorNLP:
    POSITIVAS = [
        "bullish","rally","surge","soar","gain","rise","high","record","breakout","adoption",
        "approve","launch","partner","upgrade","growth","buy","long","pump","moon","ath",
        "accumulate","institutional","etf","support","recovery"
    ]
    NEGATIVAS = [
        "bearish","crash","dump","fall","drop","low","ban","hack","scam","fraud","sell","short",
        "fear","panic","liquidation","regulation","fine","lawsuit","down","loss","warning","risk",
        "bubble","collapse","concern","investigation"
    ]

    def __init__(self):
        self.score = 0
        self.label = "Neutro"
        self.noticias = []
        self.ultima_atualizacao = None

    def atualizar(self):
        agora = datetime.now()
        if self.ultima_atualizacao and (agora - self.ultima_atualizacao).seconds < 1800:
            return
        try:
            url = "https://min-api.cryptocompare.com/data/v2/news/?lang=EN&categories=BTC,ETH&sortOrder=popular"
            r = requests.get(url, timeout=10)
            dados = r.json().get("Data", [])[:15]
            score_total = 0
            titulos = []
            for noticia in dados:
                titulo = noticia.get("title", "").lower()
                body = noticia.get("body", "").lower()[:200]
                texto = titulo + " " + body
                titulos.append(noticia.get("title", ""))
                pos = sum(1 for p in self.POSITIVAS if p in texto)
                neg = sum(1 for n in self.NEGATIVAS if n in texto)
                score_total += (pos - neg)

            self.score = max(-10, min(10, score_total))
            self.noticias = titulos[:5]
            self.ultima_atualizacao = agora

            if self.score >= 3:
                self.label = "Muito Positivo"
            elif self.score >= 1:
                self.label = "Positivo"
            elif self.score <= -3:
                self.label = "Muito Negativo"
            elif self.score <= -1:
                self.label = "Negativo"
            else:
                self.label = "Neutro"

            log.info("📰 NLP: score=%+d (%s)", self.score, self.label)
        except Exception as e:
            log.warning("⚠️ NLP falhou: %s", e)

    def ajustar_sinal(self, sinal: str) -> str:
        if self.score <= -4 and sinal == "COMPRAR":
            log.info("🚫 NLP bloqueia COMPRA")
            return "AGUARDAR"
        if self.score >= 4 and sinal == "VENDER":
            log.info("🚫 NLP bloqueia VENDA")
            return "AGUARDAR"
        return sinal
