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
    y_tf = '60m' if tf == '1h' else tf
    
    resultados = []
    for s in LISTAS.get(categoria, []):
        try:
            df = yf.download(s, period="2d", interval=y_tf, progress=False)
            if df.empty: continue
            
            close = float(df['Close'].iloc[-1])
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean().iloc[-1]
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1]
            rsi = 50 if loss == 0 else 100 - (100 / (1 + (gain / loss)))
            
            score = 80 if rsi < 35 else (20 if rsi > 65 else 50)
            resultados.append({"symbol": s, "score": int(score)})
        except Exception as e:
            continue
            
    return jsonify(sorted(resultados, key=lambda x: x['score'], reverse=True))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
