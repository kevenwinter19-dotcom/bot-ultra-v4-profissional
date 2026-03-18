import math
import time
from collections import deque
from datetime import datetime
import requests
from binance.client import Client
from binance.exceptions import BinanceAPIException

from .config import SECRETS, SECRETS_LOCK, INTERVALO, MAX_POSICOES, PARES_PADRAO, STATE_LOCK
from .state import ESTADO_GLOBAL
from .logging_setup import log
from .rl import AgenteQL
from .capital import GestaoCapital
from .nlp import AnalisadorNLP
from .news import AlphaNewsManager
from .whale import WhaleDetector
from .optimizer import AutoOtimizador
from .indicators import sinal_multi_tf

def atualizar_estado(agente, gestao, sentimento, nlp, whale, alpha_news, posicoes, otimizador, log_buffer):
    with STATE_LOCK:
        ESTADO_GLOBAL.update({
            "status": "rodando",
            "capital": round(gestao.capital, 4),
            "trades": agente.total_trades,
            "wins": agente.wins,
            "losses": agente.losses,
            "lucro_total": round(agente.lucro_total, 4),
            "sentimento": sentimento.valor,
            "fear_greed_label": sentimento.classificacao,
            "nlp_score": nlp.score,
            "nlp_label": nlp.label,
            "news_score": alpha_news.score,
            "news_label": alpha_news.label,
            "news_items": alpha_news.items,
            "whale_alertas": list(whale.alertas),
            "posicoes": {k: {
                "lado": v["lado"], "entrada": v["entrada"], "stop": v["stop"], "alvo": v["alvo"], "qtd": v["qtd"]
            } for k, v in posicoes.items()},
            "parametros": {k: str(v) for k, v in otimizador.parametros.items()},
            "ultima_otimizacao": otimizador.ultima_otimizacao.strftime("%d/%m %H:%M") if otimizador.ultima_otimizacao else "Nunca",
            "log_recente": list(log_buffer)[-40:],
        })

def run_engine(log_buffer):
    with SECRETS_LOCK:
        api_key = SECRETS.get("binance_api_key", "")
        api_secret = SECRETS.get("binance_api_secret", "")
        usar_testnet = bool(SECRETS.get("usar_testnet", True))
        capital_inicial = float(SECRETS.get("capital_total", 100.0))

    client = Client(api_key, api_secret, testnet=usar_testnet)
    agente = AgenteQL()
    gestao = GestaoCapital(capital_inicial)

    sentimento = type("S", (), {"valor": 50, "classificacao": "Neutro"})()

    def atualizar_fg():
        try:
            r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=8)
            d = r.json()["data"][0]
            sentimento.valor = int(d["value"])
            sentimento.classificacao = d["value_classification"]
            log.info("📊 Fear & Greed: %s (%s)", sentimento.valor, sentimento.classificacao)
        except Exception:
            pass

    nlp = AnalisadorNLP()
    alpha_news = AlphaNewsManager()
    whale = WhaleDetector()
    otimizador = AutoOtimizador()
    posicoes = {}
    estado_rl = {}

    atualizar_fg()
    nlp.atualizar()
    alpha_news.atualizar(PARES_PADRAO)

    ciclo = 0
    while True:
        try:
            ciclo += 1

            with STATE_LOCK:
                bot_ativo = ESTADO_GLOBAL.get("bot_ativo", True)
                pares_ativos = ESTADO_GLOBAL.get("pares_ativos", ["BTCUSDT", "ETHUSDT", "BNBUSDT"])

            if ciclo % 30 == 0:
                atualizar_fg()
                nlp.atualizar()
                alpha_news.atualizar(pares_ativos)

            if otimizador.deve_otimizar():
                otimizador.otimizar(client)

            if not gestao.pode_operar():
                log.warning("🛑 DRAWDOWN %.1f%% - bot pausado", gestao.drawdown() * 100)
                atualizar_estado(agente, gestao, sentimento, nlp, whale, alpha_news, posicoes, otimizador, log_buffer)
                time.sleep(300)
                continue

            for par in list(posicoes.keys()):
                pos = posicoes[par]
                try:
                    preco = float(client.get_symbol_ticker(symbol=par)["price"])
                    entrada = pos["entrada"]
                    lado = pos["lado"]

                    pnl_pct = (preco - entrada) / entrada if lado == "COMPRAR" else (entrada - preco) / entrada
                    pnl_usd = pnl_pct * pos["qtd"] * entrada

                    fechar = False
                    if lado == "COMPRAR":
                        fechar = preco <= pos["stop"] or preco >= pos["alvo"]
                    else:
                        fechar = preco >= pos["stop"] or preco <= pos["alvo"]

                    if fechar:
                        lado_f = "SELL" if lado == "COMPRAR" else "BUY"
                        try:
                            client.order_market(symbol=par, side=lado_f, quantity=pos["qtd"])
                        except BinanceAPIException as e:
                            log.error("Erro fechando %s: %s", par, e.message)

                        novo_cap = gestao.capital + pnl_usd
                        gestao.atualizar(novo_cap)
                        gestao.historico_retornos.append(pnl_pct)

                        if par in estado_rl:
                            recompensa = math.log1p(max(-0.99, pnl_pct * 100)) if pnl_usd > 0 else -2.5 * abs(pnl_pct * 100)
                            agente.aprender(estado_rl[par], pos["acao_idx"], recompensa, estado_rl[par])

                        agente.registrar(pnl_usd, gestao.capital)
                        del posicoes[par]
                        log.info("🔔 %s fechado | PnL: $%+.4f", par, pnl_usd)
                except Exception as e:
                    log.error("Erro monitorando %s: %s", par, e)

            sinais_dashboard = {}
            if bot_ativo:
                for par in pares_ativos:
                    if par in posicoes:
                        continue
                    if len(posicoes) >= MAX_POSICOES:
                        break
                    try:
                        sinal, score, sinais_tf, atr, preco, df_m15 = sinal_multi_tf(client, par)
                        sinais_dashboard[par] = {"timeframes": sinais_tf, "score": score}

                        if sinal == "AGUARDAR":
                            continue
                        sinal = nlp.ajustar_sinal(sinal)
                        if sinal == "AGUARDAR":
                            continue

                        sinal, whale_ratio = whale.ajustar_sinal(sinal, par, df_m15)
                        if sinal == "AGUARDAR":
                            continue

                        news_bias = alpha_news.pair_bias(par)
                        if sinal == "COMPRAR" and news_bias <= -0.20:
                            log.info("📰 [%s] notícia contradiz COMPRA | bias=%+.3f", par, news_bias)
                            continue
                        if sinal == "VENDER" and news_bias >= 0.20:
                            log.info("📰 [%s] notícia contradiz VENDA | bias=%+.3f", par, news_bias)
                            continue

                        if sentimento.valor <= 20 and sinal == "VENDER":
                            continue
                        if sentimento.valor >= 80 and sinal == "COMPRAR":
                            continue

                        estado = agente.codificar_estado(score, sentimento.valor, nlp.score, whale_ratio)
                        acao_idx = agente.escolher_acao(estado, sinal)
                        acao = agente.ACOES[acao_idx]
                        if acao not in ("COMPRAR", "VENDER"):
                            continue

                        mult_stop = otimizador.parametros["atr_stop_mult"]
                        mult_tp = otimizador.parametros["atr_tp_mult"]
                        pct_sl = atr * mult_stop / preco if preco else 0
                        pct_tp = atr * mult_tp / preco if preco else 0

                        if acao == "COMPRAR":
                            stop = round(preco * (1 - pct_sl), 2)
                            alvo = round(preco * (1 + pct_tp), 2)
                        else:
                            stop = round(preco * (1 + pct_sl), 2)
                            alvo = round(preco * (1 - pct_tp), 2)

                        _, qtd = gestao.tamanho(preco, stop)
                        if qtd <= 0:
                            continue

                        lado = "BUY" if acao == "COMPRAR" else "SELL"
                        try:
                            client.order_market(symbol=par, side=lado, quantity=qtd)
                            log.info("✅ [%s] %s %s @ $%.2f | Stop=$%s Alvo=$%s | Score=%+d | News=%+.3f",
                                     par, acao, qtd, preco, stop, alvo, score, news_bias)
                            posicoes[par] = {
                                "lado": acao, "entrada": preco, "stop": stop,
                                "alvo": alvo, "qtd": qtd, "acao_idx": acao_idx
                            }
                            estado_rl[par] = estado
                        except BinanceAPIException as e:
                            log.error("❌ [%s] %s", par, e.message)
                    except Exception as e:
                        log.error("Erro %s: %s", par, e)
                    time.sleep(1)

            with STATE_LOCK:
                ESTADO_GLOBAL["ultimo_sinal"] = sinais_dashboard
            atualizar_estado(agente, gestao, sentimento, nlp, whale, alpha_news, posicoes, otimizador, log_buffer)
            time.sleep(INTERVALO)

        except KeyboardInterrupt:
            with STATE_LOCK:
                ESTADO_GLOBAL["status"] = "encerrado"
            log.info("🛑 Bot encerrado.")
            break
        except Exception as e:
            log.error("❌ Erro geral: %s", e)
            time.sleep(30)
