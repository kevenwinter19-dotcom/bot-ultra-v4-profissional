# BOT ULTRA v4.0

Estrutura profissional do BOT ULTRA com:

- lógica principal preservada
- dashboard mobile-first
- Alpha Vantage integrada
- notícias como filtro de confiança da IA
- organização em módulos

## Estrutura

- `app.py` bootstrap
- `bot/main.py` inicialização
- `bot/engine.py` loop principal
- `bot/dashboard.py` servidor HTTP
- `bot/indicators.py` indicadores e multi-timeframe
- `bot/news.py` Alpha Vantage
- `bot/nlp.py` NLP de notícias
- `bot/whale.py` detecção de whale
- `bot/optimizer.py` auto-otimização
- `bot/rl.py` Q-learning
- `bot/capital.py` gestão de risco
- `templates/dashboard_admin.html` painel
- `secrets.json` configurações locais

## Uso

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Dashboard

Abra:

`http://SEU_IP:8080`

## Observações

A Alpha Vantage já está preenchida no `secrets.json` com a key enviada na conversa.
Troque as chaves da Binance antes de usar.

## Git

Suba usando:
- `secrets.example.json` no repositório
- `secrets.json` localmente ignorado pelo `.gitignore`
