import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/analise', methods=['GET'])
def analisar():
    symbol = request.args.get('symbol', 'EURUSD').upper().replace('/', '')
    
    # 1. Tenta buscar via Binance (Cripto)
    try:
        pair = symbol if symbol.endswith('USDT') else f"{symbol}USDT"
        url = f"https://api.binance.com/api/v3/klines?symbol={pair}&interval=1h&limit=20"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            fechamentos = [float(v[4]) for v in data]
            return processar_sinal(symbol, fechamentos, 'Binance')
    except Exception:
        pass

    # 2. Tenta buscar via API de Câmbio (Forex)
    try:
        base = symbol[:3]
        target = symbol[3:] if len(symbol) >= 6 else 'USD'
        url = f"https://api.exchangerate-api.com/v4/latest/{base}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            rates = res.json().get('rates', {})
            cotacao = rates.get(target)
            if cotacao:
                fechamentos = [cotacao] * 20
                return processar_sinal(f"{base}/{target}", fechamentos, 'Forex API')
    except Exception:
        pass

    return jsonify({"erro": "Ativo não encontrado"}), 404

def processar_sinal(ativo, fechamentos, fonte):
    preco_atual = fechamentos[-1]
    media = sum(fechamentos) / len(fechamentos)
    sinal = "COMPRA" if preco_atual >= media else "VENDA"
    diff = abs((preco_atual - media) / media) * 100 if media != 0 else 0
    score = min(98, max(70, int(70 + (diff * 15))))
    
    return jsonify({
        "ativo": ativo,
        "fonte": fonte,
        "sinal": sinal,
        "score": score,
        "probabilidade": score - 2,
        "casos": len(fechamentos)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
