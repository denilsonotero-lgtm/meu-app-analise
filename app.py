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

@app.route('/api/analise', methods=['GET'])
def analisar():
    symbol = request.args.get('symbol', 'EURUSD').upper().replace('/', '')
    timeframe = request.args.get('timeframe', '1h').lower()
    
    # Mapeamento de timeframes para a API
    tf_map = {
        '5m': '5m',
        '15m': '15m',
        '1h': '60m',
        '4h': '1h',
        '1d': '1d'
    }
    intervalo = tf_map.get(timeframe, '60m')
    
    # Ajuste de símbolo para Forex/Cripto
    ticker_symbol = symbol
    if not symbol.endswith('=X') and not symbol.endswith('-USD'):
        if 'USD' in symbol and len(symbol) == 6:
            ticker_symbol = f"{symbol}=X"
        elif 'BTC' in symbol or 'ETH' in symbol:
            ticker_symbol = f"{symbol[:3]}-USD"

    try:
        # Busca histórico do mercado
        data = yf.download(tickers=ticker_symbol, period="5d", interval=intervalo, progress=False)
        
        if data.empty or len(data) < 15:
            return jsonify({"erro": "Ativo não encontrado ou dados insuficientes"}), 404

        # Tratamento de colunas do DataFrame
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # Cálculo de Indicadores
        df_close = data['Close']
        rsi_series = ta.rsi(df_close, length=14)
        ema_series = ta.ema(df_close, length=9)

        if rsi_series is None or ema_series is None or rsi_series.empty or ema_series.empty:
            return jsonify({"erro": "Falha no cálculo dos indicadores"}), 500

        rsi = float(rsi_series.iloc[-1])
        ema_9 = float(ema_series.iloc[-1])
        preco_atual = float(df_close.iloc[-1])

        # Lógica do Score e Sinal
        score = 50
        sinal = "OBSERVAR"

        if preco_atual > ema_9:
            score += 20
        else:
            score -= 20

        if rsi < 30:
            score += 25
            sinal = "COMPRA"
        elif rsi > 70:
            score -= 25
            sinal = "VENDA"
        else:
            if score >= 65:
                sinal = "COMPRA"
            elif score <= 35:
                sinal = "VENDA"

        score_final = min(99, max(10, int(score)))

        # Cálculo de Stop Loss e Take Profit
        fator_sl = 0.985 if sinal == "COMPRA" else 1.015
        fator_tp = 1.03 if sinal == "COMPRA" else 0.97

        return jsonify({
            "ativo": symbol,
            "fonte": "Yahoo Finance",
            "timeframe": timeframe,
            "sinal": sinal,
            "score": score_final,
            "probabilidade": min(95, score_final + 2),
            "casos": len(data),
            "rsi": round(rsi, 2),
            "preco_atual": round(preco_atual, 4),
            "take_profit": round(preco_atual * fator_tp, 4),
            "stop_loss": round(preco_atual * fator_sl, 4)
        })

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
