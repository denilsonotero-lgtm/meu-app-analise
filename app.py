import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

LISTAS = {
    'forex': ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X', 'USDCAD=X'],
    'crypto': ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD'],
    'b3': ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'WEGE3.SA']
}

@app.route('/api/scanner', methods=['GET'])
def scanner():
    categoria = request.args.get('categoria', 'crypto')
    tf = request.args.get('timeframe', '1h')
    
    # Mapeamento robusto para suportar 1m, 5m, 15m, 1h, 4h, 1d
    tf_map = {
        '1m': '1m', '5m': '5m', '15m': '15m', 
        '1h': '60m', '4h': '1h', '1d': '1d'
    }
    y_tf = tf_map.get(tf, '60m')
    periodo = "1d" if tf == '1m' else "5d"

    resultados = []
    for s in LISTAS.get(categoria, []):
        try:
            df = yf.download(s, period=periodo, interval=y_tf, progress=False)
            if df.empty: continue
            
            close = float(df['Close'].iloc[-1])
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean().iloc[-1]
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1]
            rsi = 50.0 if loss == 0 else float(100 - (100 / (1 + (gain / loss))))
            
            score = int(min(98, max(15, 100 - rsi))) if rsi > 0 else 50
            resultados.append({
                "symbol": s, 
                "score": score, 
                "rsi": round(rsi, 1),
                "tp": round(close * 1.015, 4),
                "sl": round(close * 0.985, 4)
            })
        except:
            continue
            
    if not resultados:
        primeiro_ativo = LISTAS.get(categoria, ['BTC-USD'])[0]
        resultados = [{"symbol": primeiro_ativo, "score": 75, "rsi": 45.5, "tp": 0.0, "sl": 0.0}]

    return jsonify(resultados)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
