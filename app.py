import os
import yfinance as yf
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Lista de ativos para o scanner automático
LISTAS = {
    'crypto': ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD', 'ADA-USD', 'DOGE-USD'],
    'forex': ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', '^IXIC', '^GSPC', '^DJI', 'GOLD'],
    'b3': ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'ABEV3.SA', 'WEGE3.SA']
}

def calcular_score(data):
    # Lógica de score baseada em tendência e RSI
    rsi = data['rsi']
    tendencia = data['tendencia']
    score = 50
    if tendencia == "ALTA": score += 20
    else: score -= 20
    if rsi < 35: score += 25
    elif rsi > 65: score -= 25
    return min(98, max(20, int(score)))

def analisar_ativo(symbol, interval):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="5d", interval="1h" if interval == '60m' else interval)
        if data.empty: return None
        
        close = data['Close'].iloc[-1]
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs.iloc[-1]))
        
        tendencia = "ALTA" if close > data['Close'].rolling(9).mean().iloc[-1] else "BAIXA"
        
        return {
            "symbol": symbol,
            "rsi": round(float(rsi), 2),
            "tendencia": tendencia,
            "score": calcular_score({"rsi": rsi, "tendencia": tendencia}),
            "preco": round(float(close), 4)
        }
    except: return None

@app.route('/api/scanner', methods=['GET'])
def scanner():
    categoria = request.args.get('categoria', 'crypto')
    ativos = LISTAS.get(categoria, LISTAS['crypto'])
    
    resultados = []
    for ativo in ativos:
        res = analisar_ativo(ativo, '60m')
        if res: resultados.append(res)
    
    # Ordena pelo score (maior primeiro)
    resultados.sort(key=lambda x: x['score'], reverse=True)
    return jsonify(resultados[:5]) # Retorna os top 5

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
