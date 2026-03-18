import numpy as np
import pandas as pd
from datetime import datetime
from binance.client import Client
from .indicators import calcular_indicadores
from .logging_setup import log

class AutoOtimizador:
    def __init__(self):
        self.parametros = {
            "threshold_score": 7,
            "rsi_oversold": 35,
            "rsi_overbought": 65,
            "atr_stop_mult": 2.0,
            "atr_tp_mult": 4.0,
        }
        self.ultima_otimizacao = None
        self.intervalo_horas = 24

    def deve_otimizar(self):
        if self.ultima_otimizacao is None:
            return True
        return (datetime.now() - self.ultima_otimizacao).seconds >= self.intervalo_horas * 3600

    def backtest_rapido(self, df, params):
        retornos = []
        i = 50
        while i < len(df) - 20:
            u = df.iloc[i]
            p1 = df.iloc[i - 1]
            s = 0
            if u["ema9"] > u["ema21"] > u["ema50"]:
                s += 3
            elif u["ema9"] < u["ema21"] < u["ema50"]:
                s -= 3
            if u["rsi"] < params["rsi_oversold"]:
                s += 2
            elif u["rsi"] > params["rsi_overbought"]:
                s -= 2
            if p1["macd_hist"] <= 0 and u["macd_hist"] > 0:
                s += 2
            elif p1["macd_hist"] >= 0 and u["macd_hist"] < 0:
                s -= 2

            if abs(s) >= params["threshold_score"]:
                lado = 1 if s > 0 else -1
                entrada = u["close"]
                atr = u["atr"]
                stop = entrada - lado * atr * params["atr_stop_mult"]
                alvo = entrada + lado * atr * params["atr_tp_mult"]

                for j in range(i + 1, min(i + 40, len(df))):
                    p = df.iloc[j]["close"]
                    pnl = (p - entrada) * lado
                    if lado == 1 and (p <= stop or p >= alvo):
                        retornos.append(pnl / entrada)
                        break
                    elif lado == -1 and (p >= stop or p <= alvo):
                        retornos.append(pnl / entrada)
                        break
                i += 15
            else:
                i += 1

        if len(retornos) < 5:
            return 0.0
        r = np.array(retornos)
        return float(np.mean(r) / (np.std(r) + 1e-9))

    def otimizar(self, client, par="BTCUSDT"):
        log.info("🔬 Iniciando auto-otimização...")
        try:
            klines = client.get_klines(symbol=par, interval=Client.KLINE_INTERVAL_15MINUTE, limit=500)
            df = pd.DataFrame(klines, columns=[
                "time","open","high","low","close","volume",
                "close_time","quote_vol","trades","taker_base","taker_quote","ignore"
            ])
            for col in ["open","high","low","close","volume"]:
                df[col] = df[col].astype(float)
            df = calcular_indicadores(df)

            grade = {
                "threshold_score": [5, 6, 7, 8],
                "rsi_oversold": [30, 35, 40],
                "rsi_overbought": [60, 65, 70],
                "atr_stop_mult": [1.5, 2.0, 2.5],
                "atr_tp_mult": [3.0, 4.0, 5.0],
            }

            melhor_sharpe = -999
            melhores_params = self.parametros.copy()
            for _ in range(30):
                params = {k: np.random.choice(v) for k, v in grade.items()}
                sharpe = self.backtest_rapido(df, params)
                if sharpe > melhor_sharpe:
                    melhor_sharpe = sharpe
                    melhores_params = params.copy()

            self.parametros = melhores_params
            self.ultima_otimizacao = datetime.now()
            log.info("✅ Otimização | Sharpe=%.3f | %s", melhor_sharpe, melhores_params)
            return melhores_params
        except Exception as e:
            log.error("Erro na otimização: %s", e)
            return self.parametros
