import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from websocket import create_connection

app = Flask(__name__)
CORS(app)

XTB_USER = os.getenv("XTB_USER")
XTB_PASS = os.getenv("XTB_PASS")

@app.route('/api/xtb', methods=['GET'])
def get_xtb_data():
    symbol = request.args.get('symbol', 'EURUSD').upper()
    
    if not XTB_USER or not XTB_PASS:
        return jsonify({"erro": "Credenciais XTB não configuradas no Render"}), 500

    try:
        # Conecta ao WebSocket da XTB (Demo)
        ws = create_connection("wss://ws.xtb.com/demo")
        
        # Envia comando de Login
        login_cmd = {
            "command": "login",
            "arguments": {"userId": XTB_USER, "password": XTB_PASS}
        }
        ws.send(json.dumps(login_cmd))
        res_login = json.loads(ws.recv())

        if not res_login.get("status"):
            ws.close()
            return jsonify({"erro": "Falha de autenticação na XTB"}), 400

        # Solicita os últimos dados do gráfico
        chart_cmd = {
            "command": "getChartLastRequest",
            "arguments": {
                "info": {
                    "period": 60,
                    "start": 0,
                    "symbol": symbol
                }
            }
        }
        ws.send(json.dumps(chart_cmd))
        res_chart = json.loads(ws.recv())
        ws.close()

        # Processa os dados recebidos
        rate_infos = res_chart.get("returnData", {}).get("rateInfos", [])
        if not rate_infos:
            return jsonify({"erro": "Ativo não encontrado"}), 404

        fechamentos = [v["open"] for v in rate_infos]
        preco_atual = fechamentos[-1]
        media = sum(fechamentos) / len(fechamentos)
        
        sinal = "COMPRA" if preco_atual >= media else "VENDA"
        diff = abs((preco_atual - media) / media) * 100
        score = min(98, max(70, int(70 + (diff * 15))))

        return jsonify({
            "sinal": sinal,
            "score": score,
            "probabilidade": score - 2,
            "casos": len(fechamentos)
        })

    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
