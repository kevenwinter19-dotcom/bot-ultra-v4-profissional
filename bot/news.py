import requests
from .config import SECRETS, SECRETS_LOCK
from .logging_setup import log

class AlphaNewsManager:
    def __init__(self):
        self.items = []
        self.score = 0.0
        self.label = "Neutro"
        self.last_update = None

    def _pair_keywords(self, pair):
        pair = pair.upper()
        mapping = {
            "BTCUSDT": ["bitcoin", "btc"],
            "ETHUSDT": ["ethereum", "eth"],
            "BNBUSDT": ["binance", "bnb", "binance coin"],
        }
        return mapping.get(pair, [pair.replace("USDT", "").lower()])

    def _score_item(self, item, pair):
        title = (item.get("title") or "").lower()
        summary = (item.get("summary") or "").lower()
        text = title + " " + summary
        rel = sum(1 for kw in self._pair_keywords(pair) if kw in text)

        sentiment = 0.0
        for sent in item.get("ticker_sentiment", []) or []:
            t = (sent.get("ticker") or "").upper()
            if pair.startswith("BTC") and t == "BTC":
                sentiment = float(sent.get("ticker_sentiment_score") or 0)
                break
            if pair.startswith("ETH") and t == "ETH":
                sentiment = float(sent.get("ticker_sentiment_score") or 0)
                break
            if pair.startswith("BNB") and t == "BNB":
                sentiment = float(sent.get("ticker_sentiment_score") or 0)
                break

        if sentiment == 0.0:
            sentiment = float(item.get("overall_sentiment_score") or 0)
        return round(sentiment * (1 + min(rel, 2) * 0.35), 4)

    def atualizar(self, pares):
        with SECRETS_LOCK:
            api_key = SECRETS.get("alpha_vantage_api_key", "")
        if not api_key:
            self.items = []
            self.score = 0.0
            self.label = "Sem API"
            return

        all_items = []
        total_score = 0.0

        for pair in pares[:5]:
            try:
                url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&topics=blockchain,cryptocurrency&limit=10&sort=LATEST&apikey={api_key}"
                r = requests.get(url, timeout=6)
                data = r.json()
                feed = data.get("feed", [])[:10]
                scored = []
                for item in feed:
                    sc = self._score_item(item, pair)
                    scored.append((sc, item))
                scored.sort(key=lambda x: abs(x[0]), reverse=True)
                total_score += round(sum(sc for sc, _ in scored[:3]), 4)
                for sc, item in scored[:3]:
                    all_items.append({
                        "pair": pair,
                        "score": sc,
                        "title": item.get("title"),
                        "source": item.get("source"),
                        "summary": (item.get("summary") or "")[:220],
                        "time_published": item.get("time_published"),
                        "overall_sentiment_label": item.get("overall_sentiment_label"),
                    })
            except Exception as e:
                log.warning("⚠️ Alpha falhou para %s: %s", pair, e)

        all_items.sort(key=lambda x: abs(x["score"]), reverse=True)
        self.items = all_items[:9]
        self.score = round(total_score, 4)
        if self.score >= 0.6:
            self.label = "Positivo"
        elif self.score <= -0.6:
            self.label = "Negativo"
        else:
            self.label = "Neutro"
        log.info("📰 Alpha: %s notícias | score=%s | %s", len(self.items), self.score, self.label)

    def pair_bias(self, pair):
        rel = [x for x in self.items if x.get("pair") == pair]
        if not rel:
            return 0.0
        return round(sum(float(x.get("score") or 0) for x in rel[:3]), 4)
