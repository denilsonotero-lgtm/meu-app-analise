import yfinance as yf
import pandas as pd
import os

# Lista de ativos para compor sua base de conhecimento
ATIVOS = ['BTC-USD', 'EURUSD=X', 'PETR4.SA', 'VALE3.SA', 'ETH-USD']

def coletar_dados():
    if not os.path.exists('base_historica'):
        os.makedirs('base_historica')
    
    for ativo in ATIVOS:
        print(f"Coletando histórico de 5 anos: {ativo}...")
        try:
            # Baixa dados de 5 anos com intervalo de 1 hora
            df = yf.download(ativo, period="5y", interval="1h", progress=False)
            
            # Limpeza básica: remover linhas vazias
            df.dropna(inplace=True)
            
            # Salva o arquivo CSV para usar no motor de busca
            df.to_csv(f'base_historica/{ativo.replace("=", "_").replace(".", "_")}.csv')
            print(f"Sucesso: {ativo} salvo com {len(df)} registros.")
        except Exception as e:
            print(f"Erro ao baixar {ativo}: {e}")

if __name__ == '__main__':
    coletar_dados()
