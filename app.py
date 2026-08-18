import yfinance as yf
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import numpy as np
from motor_inteligente import prever_com_historico

app = Flask(__name__)
CORS(app)

# Listas expandidas com 10 ativos principais para cada categoria
LISTAS = {
    'forex': ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X', 'AUDUSD=X', 'USDCAD=X', 'USDCHF=X', 'NZDUSD=X', 'EURGBP=X', 'EURJPY=X', 'GBPJPY=X'],
    'crypto': ['BTC-USD', 'ETH-USD', 'SOL-USD', 'BNB-USD', 'XRP-USD', 'ADA-USD', 'DOGE-USD', 'AVAX-USD', 'DOT-USD', 'LINK-USD'],
    'b3': ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'WEGE3.SA', 'BBAS3.SA', 'ABEV3.SA', 'RENT3.SA', 'JBSS3.SA', 'MGLU3.SA']
}

def calcular_fibonacci(df):
    high = df['High'].max()
    low = df['Low'].min()
    diff = high - low
    return {
        'fib_618': high - (diff * 0.618)
    }

def identificar_padrao_candle(df):
    if len(df) < 2: return "NEUTRO"
    close_atual = df['Close'].iloc[-1]
    open_atual = df['Open'].iloc[-1]
    close_anterior = df['Close'].iloc[-2]
    open_anterior = df['Open'].iloc[-2]
    if close_atual > open_atual and close_anterior < open_anterior and close_atual >= open_anterior and open_atual <= close_anterior:
        return "ENGOLFO DE ALTA 🟢"
    elif close_atual < open_atual and close_anterior > open_anterior and close_atual <= open_anterior and close_atual >= open_anterior:
        return "ENGOLFO DE BAIXA 🔴"
    return "PADRÃO NORMAL ⚖️"

def motor_de_confluencia(df, symbol):
    close = df['Close'].iloc[-1]
    
    delta = df['Close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean().iloc[-1]
    loss = -delta.clip(upper=0).rolling(14).mean().iloc[-1]
    rsi = 100 - (100 / (1 + (gain / loss))) if loss != 0 else 50
    
    ema12 = df['Close'].ewm(span=12).mean().iloc[-1]
    ema26 = df['Close'].ewm(span=26).mean().iloc[-1]
    macd = ema12 - ema26
    signal = macd * 0.9 
    
    fibs = calcular_fibonacci(df)
    perto_suporte_fib = abs(close - fibs['fib_618']) / close < 0.005 
    padrao_candle = identificar_padrao_candle(df)
    
    score_tecnico = 50 
    if rsi < 30: score_tecnico += 20
    elif rsi > 70: score_tecnico -= 20 
    if macd > signal: score_tecnico += 15
    else: score_tecnico -= 15
    if perto_suporte_fib: score_tecnico += 10
    if "ALTA" in padrao_candle: score_tecnico += 10
    elif "BAIXA" in padrao_candle: score_tecnico -= 10
    score_tecnico = int(min(99, max(10, score_tecnico)))

    score_hist, amostras = prever_com_historico(df, symbol)

    score_final = int((score_tecnico * 0.6) + (score_hist * 0.4))
    score_final = int(min(99, max(10, score_final)))

    direcao = "COMPRA FORTE 🚀" if score_final >= 70 else ("VENDA FORTE 📉" if score_final <= 30 else "AGUARDAR / LATERAL ⚖️")
    
    return {
        "score": score_final,
        "rsi": round(float(rsi), 1),
        "tendencia": direcao,
        "candle": padrao_candle,
        "fib_relevante": round(float(fibs['fib_618']), 2),
        "amostras_hist": amostras
    }

@app.route('/')
def home():
    return "API do Quantum Dopm Pro está online e funcionando!"

@app.route('/api/scanner', methods=['GET'])
def scanner():
    cat = request.args.get('categoria', 'crypto').lower()
    busca = request.args.get('busca', '').strip().upper()
    min_score = int(request.args.get('score_min', 0))
    
    # Define os ativos a varrer
    if busca:
        ativos = [busca]
    else:
        ativos = LISTAS.get(cat, LISTAS['crypto'])
        
    resultados = []
    
    for s in ativos:
        try:
            df = yf.download(s, period="7d", interval="1h", progress=False)
            if df.empty or len(df) < 50: 
                continue
            
            analise = motor_de_confluencia(df, s)
            preco_atual = float(df['Close'].iloc[-1])
            
            # Dados estruturados para alimentar os cards e a tela de Raio-X
            ativo_info = {
                "symbol": s,
                "price": round(preco_atual, 4),
                "score": analise["score"],
                "probabilidade": analise["score"],
                "rsi": analise["rsi"],
                "tendencia": analise["tendencia"],
                "candle": analise["candle"],
                "fib_relevante": analise["fib_relevante"],
                "amostras_hist": analise["amostras_hist"],
                # Alvos automáticos para o gerenciamento de risco do Raio-X
                "entrada": round(preco_atual, 4),
                "take_profit": round(preco_atual * 1.02, 4),
                "stop_loss": round(preco_atual * 0.98, 4)
            }
            
            if analise["score"] >= min_score:
                resultados.append(ativo_info)
        except Exception as e:
            continue
            
    # Ordena do maior score para o menor e pega os 10 melhores
    resultados = sorted(resultados, key=lambda x: x['score'], reverse=True)
    return jsonify(resultados[:10])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
