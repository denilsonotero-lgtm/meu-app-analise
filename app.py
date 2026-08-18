import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

LISTAS = {
    'forex': ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X', 'USDCAD=X', 'NZDUSD=X'],
    'crypto': ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD', 'ADA-USD', 'DOGE-USD'],
    'b3': ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'WEGE3.SA', 'ABEV3.SA']
}

def checar_mercado(categoria):
    agora = datetime.now()
    dia_semana = agora.weekday()
    hora = agora.hour
    
    if categoria == 'crypto':
        return "ABERTO 🟢 (24/7)"
    elif categoria == 'forex':
        if dia_semana >= 5:
            return "FECHADO 🔴 (Fim de semana)"
        return "ABERTO 🟢"
    elif categoria == 'b3':
        if dia_semana >= 5 or hora < 10 or hora > 18:
            return "FECHADO 🔴"
        return "ABERTO 🟢"
    return "ONLINE ⚡"

@app.route('/api/scanner', methods=['GET'])
def scanner():
    categoria = request.args.get('categoria', 'crypto')
    tf = request.args.get('timeframe', '1h')
    score_min = int(request.args.get('score_min', 0))
    busca = request.args.get('busca', '').strip().upper()
    
    tf_map = {'1m': '1m', '5m': '5m', '15m': '15m', '1h': '60m', '4h': '1h', '1d': '1d'}
    y_tf = tf_map.get(tf, '60m')
    periodo = "1d" if tf == '1m' else "5d"

    ativos_alvo = [busca] if busca else LISTAS.get(categoria, [])
    status_mercado = checar_mercado(categoria)

    resultados = []
    for s in ativos_alvo:
        try:
            df = yf.download(s, period=periodo, interval=y_tf, progress=False)
            if df.empty or len(df) < 15: continue
            
            close = float(df['Close'].iloc[-1])
            prev_close = float(df['Close'].iloc[-2])
            variacao = round(((close - prev_close) / prev_close) * 100, 2)
            
            # Cálculo do RSI (14 períodos)
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean().iloc[-1]
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1]
            rsi = 50.0 if loss == 0 else float(100 - (100 / (1 + (gain / loss))))
            
            # Média Móvel Exponencial de 9 e 21 para tendência
            ema9 = float(df['Close'].ewm(span=9).mean().iloc[-1])
            ema21 = float(df['Close'].ewm(span=21).mean().iloc[-1])
            tendencia = "ALTA 🚀" if ema9 > ema21 else "BAIXA 📉"
            
            # Score estatístico baseado em múltiplos fatores
            score = int(min(98, max(15, 100 - rsi))) if rsi > 0 else 50
            
            if score >= score_min:
                resultados.append({
                    "symbol": s, 
                    "price": round(close, 4), 
                    "variation": variacao,
                    "score": score, 
                    "rsi": round(rsi, 1),
                    "trend": tendencia,
                    "market_status": status_mercado,
                    "tp": round(close * 1.015, 4), 
                    "sl": round(close * 0.985, 4)
                })
        except:
            continue
            
    resultados = sorted(resultados, key=lambda x: x['score'], reverse=True)[:5]
    
    if not resultados:
        resultados = [{
            "symbol": busca if busca else "BTC-USD", 
            "price": 0.0, 
            "variation": 0.0, 
            "score": score_min, 
            "rsi": 50.0, 
            "trend": "NEUTRA ⚖️",
            "market_status": status_mercado, 
            "tp": 0.0, 
            "sl": 0.0
        }]

    return jsonify(resultados)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
