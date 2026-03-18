import pandas as pd
from binance.client import Client

TIMEFRAMES = {
    "M5": Client.KLINE_INTERVAL_5MINUTE,
    "M15": Client.KLINE_INTERVAL_15MINUTE,
    "H1": Client.KLINE_INTERVAL_1HOUR,
}

def calcular_indicadores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    c = df["close"]; h = df["high"]; l = df["low"]

    df["ema9"] = c.ewm(span=9, adjust=False).mean()
    df["ema21"] = c.ewm(span=21, adjust=False).mean()
    df["ema50"] = c.ewm(span=50, adjust=False).mean()

    delta = c.diff()
    g = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    p = (-delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
    df["rsi"] = 100 - (100 / (1 + g / p))

    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    sma20 = c.rolling(20).mean()
    std20 = c.rolling(20).std()
    df["bb_upper"] = sma20 + 2 * std20
    df["bb_lower"] = sma20 - 2 * std20

    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    df["atr"] = tr.ewm(span=14, adjust=False).mean()

    pt = (h + l + c) / 3
    df["vwap"] = (pt * df["volume"]).cumsum() / df["volume"].cumsum()

    return df.dropna().reset_index(drop=True)

def score_tf(df: pd.DataFrame):
    u = df.iloc[-1]
    p1 = df.iloc[-2]
    s = 0

    if u["ema9"] > u["ema21"] > u["ema50"]:
        s += 3
    elif u["ema9"] < u["ema21"] < u["ema50"]:
        s -= 3

    if p1["ema9"] <= p1["ema21"] and u["ema9"] > u["ema21"]:
        s += 2
    elif p1["ema9"] >= p1["ema21"] and u["ema9"] < u["ema21"]:
        s -= 2

    if u["rsi"] < 35:
        s += 2
    elif u["rsi"] > 65:
        s -= 2
    elif u["rsi"] < 45:
        s += 1
    elif u["rsi"] > 55:
        s -= 1

    if p1["macd_hist"] <= 0 and u["macd_hist"] > 0:
        s += 2
    elif p1["macd_hist"] >= 0 and u["macd_hist"] < 0:
        s -= 2

    if u["close"] > u["vwap"]:
        s += 1
    else:
        s -= 1

    return s, u

def sinal_multi_tf(client, par: str):
    scores = {}
    ultimo_m15 = None

    for nome, tf in TIMEFRAMES.items():
        try:
            klines = client.get_klines(symbol=par, interval=tf, limit=100)
            df = pd.DataFrame(klines, columns=[
                "time","open","high","low","close","volume",
                "close_time","quote_vol","trades","taker_base","taker_quote","ignore"
            ])
            for col in ["open","high","low","close","volume"]:
                df[col] = df[col].astype(float)
            df["time"] = pd.to_datetime(df["time"], unit="ms")
            df = calcular_indicadores(df)
            s, u = score_tf(df)
            scores[nome] = {"score": s, "u": u, "df": df}
            if nome == "M15":
                ultimo_m15 = u
        except Exception:
            scores[nome] = {"score": 0, "u": None, "df": None}

    score_total = scores["M5"]["score"] + scores["M15"]["score"] + scores["H1"]["score"] * 2
    sinais_tf = {
        nome: ("COMPRAR" if d["score"] >= 4 else ("VENDER" if d["score"] <= -4 else "AGUARDAR"))
        for nome, d in scores.items()
    }

    if score_total >= 7:
        sinal = "COMPRAR"
    elif score_total <= -7:
        sinal = "VENDER"
    else:
        sinal = "AGUARDAR"

    atr = float(ultimo_m15["atr"]) if ultimo_m15 is not None else 0.0
    preco = float(ultimo_m15["close"]) if ultimo_m15 is not None else 0.0
    df_m15 = scores["M15"]["df"]
    return sinal, score_total, sinais_tf, atr, preco, df_m15
