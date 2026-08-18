import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

LISTAS = {
    'crypto': ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD'],
    'forex': ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X', 'USDCAD=X'],
    'b3': ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'WEGE3.SA']
}

@app.route('/api/scanner', methods=['GET'])
def scanner():
    categoria = request.args.get('categoria', 'crypto')
    tf = request.args.get('timeframe', '1h')
    
    # Mapeamento do yfinance
    y_tf = '60m' if tf == '1h' else tf
    
    resultados = []
    for s in LISTAS.get(categoria, []):
        try:
            # Pega apenas os últimos 20 candles para ser super rápido
            df = yf.download(s, period="5d", interval=y_tf, progress=False)
            if df.empty: continue
            
            # Cálculo de RSI simplificado
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs.iloc[-1]))
            
            # Score fake mas rápido pra teste
            score = 60 if rsi < 40 else 40
            resultados.append({"symbol": s, "score": int(score)})
        except: continue
        
    return jsonify(sorted(resultados, key=lambda x: x['score'], reverse=True))

if __name__ == '__main__':
    app.run(port=5000)
