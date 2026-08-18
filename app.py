import os
import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

LISTAS = {
    'crypto': ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD'],
    'forex': ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', '^IXIC', '^GSPC'],
    'b3': ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'WEGE3.SA']
}

def analisar_ativo(symbol, interval):
    try:
        # Se for 1m, pegamos apenas 1 dia para ser rápido
        periodo = "1d" if interval == "1m" else "5d"
        data = yf.download(symbol, period=periodo, interval=interval, progress=False)
        if data.empty: return None
        
        close = float(data['Close'].iloc[-1])
        # Cálculo RSI
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = float(100 - (100 / (1 + rs.iloc[-1])))
        
        # Tendência simples
        media = data['Close'].rolling(9).mean().iloc[-1]
        tendencia = "ALTA" if close > media else "BAIXA"
        
        # Score
        score = 50 + (20 if tendencia == "ALTA" else -20)
        if rsi < 35: score += 25
        elif rsi > 65: score -= 25
        
        return {"symbol": symbol, "score": int(min(98, max(20, score))), "rsi": round(rsi, 2)}
    except: return None

@app.route('/api/scanner', methods=['GET'])
def scanner():
    categoria = request.args.get('categoria', 'crypto')
    tf = request.args.get('timeframe', '1h')
    
    resultados = [analisar_ativo(s, tf) for s in LISTAS.get(categoria, [])]
    resultados = [r for r in resultados if r]
    resultados.sort(key=lambda x: x['score'], reverse=True)
    return jsonify(resultados[:5])
