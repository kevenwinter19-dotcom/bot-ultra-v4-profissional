from collections import deque
from datetime import datetime
from .logging_setup import log

class WhaleDetector:
    def __init__(self, multiplicador=3.0, janela=20):
        self.multiplicador = multiplicador
        self.janela = janela
        self.alertas = deque(maxlen=20)

    def analisar(self, df, par):
        if len(df) < self.janela + 1:
            return False, 1.0
        vol_atual = df["volume"].iloc[-1]
        vol_media = df["volume"].iloc[-(self.janela + 1):-1].mean()
        ratio = vol_atual / vol_media if vol_media > 0 else 1.0
        if ratio >= self.multiplicador:
            direcao = "COMPRA" if df["close"].iloc[-1] > df["open"].iloc[-1] else "VENDA"
            alerta = {"par": par, "tipo": f"Volume {direcao}", "volume_x": round(ratio, 1), "hora": datetime.now().strftime("%H:%M:%S")}
            self.alertas.append(alerta)
            log.info("🐋 WHALE ALERT: %s | Volume %.1fx | %s", par, ratio, direcao)
            return True, ratio
        return False, ratio

    def ajustar_sinal(self, sinal, par, df):
        whale, ratio = self.analisar(df, par)
        if whale:
            ultimo = df.iloc[-1]
            direcao_whale = "COMPRAR" if ultimo["close"] > ultimo["open"] else "VENDER"
            if direcao_whale == sinal:
                log.info("🐋 Whale confirma %s em %s", sinal, par)
                return sinal, ratio
            log.info("🐋 Whale contradiz sinal em %s", par)
            return "AGUARDAR", ratio
        return sinal, ratio
