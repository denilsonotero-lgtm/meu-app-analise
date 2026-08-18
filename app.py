import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np

app = Flask(__name__)
CORS(app)

LISTAS = {
    'forex': ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X', 'USDCAD=X'],
    'crypto': ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD'],
    'b3': ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'WEGE3.SA']
}

def calcular_fibonacci(df):
    """Calcula níveis de retração de Fibonacci com base na máxima e mínima do período recente."""
    high = df['High'].max()
    low = df['Low'].min()
    diff = high - low
    
    # Níveis clássicos de Fibonacci
    fib_levels = {
        'fib_0': low,
        'fib_236': high - (diff * 0.236),
        'fib_382': high - (diff * 0.382),
        'fib_500': high - (diff * 0.5),
        'fib_618': high - (diff * 0.618),
        'fib_100': high
    }
    return fib_levels

def identificar_padrao_candle(df):
    """Identifica padrões simples de candles na última barra (Engolfo e Rejeição)."""
    if len(df) < 2: return "NEUTRO"
    
    close_atual = df['Close'].iloc[-1]
    open_atual = df['Open'].iloc[-1]
    close_anterior = df['Close'].iloc[-2]
    open_anterior = df['Open'].iloc[-2]
    
    # Engolfo de Alta
    if close_atual > open_atual and close_anterior < open_anterior and close_atual >= open_anterior and open_atual <= close_anterior:
        return "ENGOLFO DE ALTA 🟢"
    # Engolfo de Baixa
    elif close_atual < open_atual and close_anterior > open_anterior and close_atual <= open_anterior and open_atual >= close_anterior:
        return "ENGOLFO DE BAIXA 🔴"
    
    return "PADRÃO NORMAL ⚖️"

def motor_de_confluencia(df):
    """Processa todas as camadas de análise para gerar um score de 0 a 100."""
    close = df['Close'].iloc[-1]
    
    # 1. RSI (14)
    delta = df['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean().iloc[-1]
    loss = -delta.clip(upper=0).rolling(14).mean().iloc[-1]
    rsi = 100 - (100 / (1 + (gain / loss))) if loss != 0 else 50
    
    # 2. MACD
    ema12 = df['Close'].ewm(span=12).mean().iloc[-1]
    ema26 = df['Close'].ewm(span=26).mean().iloc[-1]
    macd = ema12 - ema26
    signal = macd * 0.9 # Simulação simplificada de linha de sinal para cruzamento
    
    # 3. Bandas de Bollinger
    sma20 = df['Close'].rolling(20).mean().iloc[-1]
    std20 = df['Close'].rolling(20).std().iloc[-1]
    upper_band = sma20 + (std20 * 2)
    lower_band = sma20 - (std20 * 2)
    
    # 4. Fibonacci
    fibs = calcular_fibonacci(df)
    perto_suporte_fib = abs(close - fibs['fib_618']) / close < 0.005 # Perto de 61.8%
    
    # 5. Candlestick
    padrao_candle = identificar_padrao_candle(df)
    
    # --- PONDERAÇÃO DE CONFLUÊNCIA (SCORE) ---
    score = 50 # Base neutra
    
    # Pesos do RSI
    if rsi < 30: score += 20  # Sobreventa (Oportunidade de Compra)
    elif rsi > 70: score -= 20 # Sobrecompra (Oportunidade de Venda)
    
    # Pesos do MACD
    if macd > signal: score += 15
    else: score -= 15
    
    # Pesos de Bollinger
    if close <= lower_band: score += 15 # Tocou o fundo do canal
    elif close >= upper_band: score -= 15 # Tocou o topo do canal
    
    # Pesos de Fibonacci
    if perto_suporte_fib: score += 10
    
    # Pesos de Candles
    if "ALTA" in padrao_candle: score += 10
    elif "BAIXA" in padrao_candle: score -= 10
    
    # Normalizar score entre 10 e 99
    score_final = int(min(99, max(10, score)))
    
    # Direção da Tendência baseada na confluência
    direcao = "COMPRA FORTE 🚀" if score_final >= 70 else ("VENDA FORTE 📉" if score_final <= 30 else "AGUARDAR / LATERAL ⚖️")
    
    return {
        "score": score_final,
        "rsi": round(float(rsi), 1),
        "tendencia": direcao,
        "candle": padrao_candle,
        "fib_relevante": round(float(fibs['fib_618']), 2)
    }

@app.route('/api/scanner', methods=['GET'])
def scanner():
    cat = request.args.get('categoria', 'crypto')
    busca = request.args.get('busca', '').strip().upper()
    min_score = int(request.args.get('score_min', 0))
    
    ativos = [busca] if busca else LISTAS.get(cat, [])
    resultados = []
    
    for s in ativos:
        try:
            df = yf.download(s, period="7d", interval="1h", progress=False)
            if df.empty or len(df) < 30: continue
            
            analise = motor_de_confluencia(df)
            
            if analise["score"] >= min_score:
                resultados.append({
                    "symbol": s,
                    "price": round(float(df['Close'].iloc[-1]), 4),
                    "score": analise["score"],
                    "rsi": analise["rsi"],
                    "trend": analise["tendencia"],
                    "candle": analise["candle"],
                    "fib": analise["fib_relevante"]
                })
        except:
            continue
            
    # Rankeamento: Ordena do maior score para o menor (Top melhores oportunidades)
    resultados = sorted(resultados, key=lambda x: x['score'], reverse=True)[:5]
    return jsonify(resultados)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
