import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import numpy as np

app = Flask(__name__)
CORS(app)

LISTAS = {
    'forex': ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X', 'USDCAD=X', 'NZDUSD=X', 'EURJPY=X'],
    'crypto': ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD', 'ADA-USD', 'DOGE-USD', 'AVAX-USD'],
    'b3': ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'WEGE3.SA', 'ABEV3.SA', 'RENT3.SA']
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
    periodo = "1d" if tf == '1m' else "7d"

    ativos_alvo = [busca] if busca else LISTAS.get(categoria, [])
    status_mercado = checar_mercado(categoria)

    resultados = []
    for s in ativos_alvo:
        try:
            df = yf.download(s, period=periodo, interval=y_tf, progress=False)
            if df.empty or len(df) < 35: continue
            
            close = float(df['Close'].iloc[-1])
            prev_close = float(df['Close'].iloc[-2])
            variacao = round(((close - prev_close) / prev_close) * 100, 2)
            
            # 1. RSI (14 períodos)
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean().iloc[-1]
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean().iloc[-1]
            rsi = 50.0 if loss == 0 else float(100 - (100 / (1 + (gain / loss))))
            
            # 2. EMAs de Tendência
            ema9 = float(df['Close'].ewm(span=9).mean().iloc[-1])
            ema21 = float(df['Close'].ewm(span=21).mean().iloc[-1])
            tendencia = "ALTA 🚀" if ema9 > ema21 else "BAIXA 📉"
            
            # 3. Bandas de Bollinger (20 períodos, 2 desvios)
            sma20 = df['Close'].rolling(20).mean().iloc[-1]
            std20 = df['Close'].rolling(20).std().iloc[-1]
            upper_band = float(sma20 + (std20 * 2))
            lower_band = float(sma20 - (std20 * 2))
            
            if close >= upper_band:
                pos_banda = "Topo (Resistência Extrema)"
            elif close <= lower_band:
                pos_banda = "Fundo (Suporte Extremo)"
            else:
                pos_banda = "Canal Intermediário"

            # 4. MACD (12, 26, 9)
            exp1 = df['Close'].ewm(span=12, adjust=False).mean()
            exp2 = df['Close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            macd_val = float(macd.iloc[-1])
            signal_val = float(signal.iloc[-1])
            macd_status = "BULLISH 📈" if macd_val > signal_val else "BEARISH 📉"

            # 5. Volatilidade ATR (Average True Range aproximado para Alvos Dinâmicos)
            high_low = df['High'] - df['Low']
            atr = float(high_low.rolling(14).mean().iloc[-1]) if not high_low.empty else (close * 0.01)

            # Score estatístico ponderado avançado
            base_score = int(min(95, max(20, 100 - rsi))) if rsi > 0 else 50
            if "Extremo" in pos_banda:
                base_score = min(99, base_score + 10)
            
            score = base_score
            
            if score >= score_min:
                resultados.append({
                    "symbol": s, 
                    "price": round(close, 4), 
                    "variation": variacao,
                    "score": score, 
                    "rsi": round(rsi, 1),
                    "trend": tendencia,
                    "bollinger": pos_banda,
                    "macd": macd_status,
                    "market_status": status_mercado,
                    "tp": round(close + (atr * 1.5), 4), 
                    "sl": round(close - (atr * 1.0), 4)
                })
        except:
            continue
            
    resultados = sorted(resultados, key=lambda x: x['score'], reverse=True)[:8]
    
    if not resultados:
        resultados = [{
            "symbol": busca if busca else "BTC-USD", 
            "price": 0.0, 
            "variation": 0.0, 
            "score": score_min, 
            "rsi": 50.0, 
            "trend": "NEUTRA ⚖️",
            "bollinger": "N/A",
            "macd": "NEUTRO",
            "market_status": status_mercado, 
            "tp": 0.0, 
            "sl": 0.0
        }]

    return jsonify(resultados)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
