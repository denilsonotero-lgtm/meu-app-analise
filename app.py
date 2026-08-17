import os
import json
import requests
import pandas as pd
import yfinance as yf
import pandas_ta as ta
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def extrair_dados_tf(ticker_symbol, interval):
    try:
        data = yf.download(tickers=ticker_symbol, period="5d", interval=interval, progress=False)
        if data.empty or len(data) < 15:
            return None
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        df_close = data['Close']
        rsi = ta.rsi(df_close, length=14).iloc[-1]
        ema_9 = ta.ema(df_close, length=9).iloc[-1]
        preco = df_close.iloc[-1]
        
        tendencia = "ALTA" if preco > ema_9 else "BAIXA"
        return {
            "preco": float(preco),
            "rsi": round(float(rsi), 2),
            "tendencia": tendencia
        }
    except Exception:
        return None

@app.route('/api/analise', methods=['GET'])
def analisar():
    symbol = request.args.get('symbol', 'EURUSD').upper().replace('/', '')
    tf_usuario = request.args.get('timeframe', '1h').lower()
    
    ticker_symbol = symbol
    if not symbol.endswith('=X') and not symbol.endswith('-USD'):
        if 'USD' in symbol and len(symbol) == 6:
            ticker_symbol = f"{symbol}=X"
        elif 'BTC' in symbol or 'ETH' in symbol:
            ticker_symbol = f"{symbol[:3]}-USD"

    # Mapeamento para o Yahoo Finance
    mapa_tf = {'5m': '5m', '15m': '15m', '1h': '60m', '4h': '1h', '1d': '1d'}
    
    # 1. Análise do Timeframe selecionado
    dados_principal = extrair_dados_tf(ticker_symbol, mapa_tf.get(tf_usuario, '60m'))
    if not dados_principal:
        return jsonify({"erro": "Ativo não encontrado ou dados indisponíveis"}), 404

    # 2. Comparativo Multitimeframe para o Raio-X
    tf_comparativo = {}
    for tf_key, tf_val in [('5m', '5m'), ('15m', '15m'), ('1h', '60m'), ('1d', '1d')]:
        info = extrair_dados_tf(ticker_symbol, tf_val)
        if info:
            tf_comparativo[tf_key] = f"{info['tendencia']} (RSI: {info['rsi']})"
        else:
            tf_comparativo[tf_key] = "N/A"

    rsi = dados_principal['rsi']
    preco = dados_principal['preco']
    
    # Cálculo de pontuação e sinal
    score = 50
    if dados_principal['tendencia'] == "ALTA": score += 20
    else: score -= 20

    if rsi < 35:
        score += 25
        sinal = "COMPRA"
        justificativa = "RSI em zona de sobrevenda (pressão de alta iminente)."
    elif rsi > 65:
        score -= 25
        sinal = "VENDA"
        justificativa = "RSI em zona de sobrecompra (pressão de baixa iminente)."
    else:
        sinal = "COMPRA" if score >= 50 else "VENDA"
        justificativa = "Tendência acompanhada pelas médias móveis EMA 9."

    score_final = min(98, max(20, int(score)))
    
    # Gerenciamento de Risco
    fator_sl = 0.99 if sinal == "COMPRA" else 1.01
    fator_tp = 1.02 if sinal == "COMPRA" else 0.98

    return jsonify({
        "ativo": symbol,
        "timeframe": tf_usuario,
        "sinal": sinal,
        "score": score_final,
        "probabilidade": min(95, score_final + 2),
        "rsi": rsi,
        "preco_atual": round(preco, 4),
        "take_profit": round(preco * fator_tp, 4),
        "stop_loss": round(preco * fator_sl, 4),
        "justificativa": justificativa,
        "multitimeframe": tf_comparativo
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
