import os
import pandas as pd
import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def calcular_rsi_manual(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def extrair_dados_tf(ticker_symbol, interval):
    try:
        data = yf.download(tickers=ticker_symbol, period="5d", interval=interval, progress=False)
        if data.empty or len(data) < 15:
            return None
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
            
        df_close = data['Close']
        rsi_series = calcular_rsi_manual(df_close, 14)
        rsi = rsi_series.iloc[-1]
        ema_9 = df_close.ewm(span=9, adjust=False).mean().iloc[-1]
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

    mapa_tf = {'5m': '5m', '15m': '15m', '1h': '60m', '4h': '1h', '1d': '1d'}
    
    dados_principal = extrair_dados_tf(ticker_symbol, mapa_tf.get(tf_usuario, '60m'))
    if not dados_principal:
        return jsonify({"erro": "Ativo não encontrado"}), 404

    tf_comparativo = {}
    for tf_key, tf_val in [('5m', '5m'), ('15m', '15m'), ('1h', '60m'), ('1d', '1d')]:
        info = extrair_dados_tf(ticker_symbol, tf_val)
        if info:
            tf_comparativo[tf_key] = f"{info['tendencia']} (RSI: {info['rsi']})"
        else:
            tf_comparativo[tf_key] = "N/A"

    rsi = dados_principal['rsi']
    preco = dados_principal['preco']
    
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
