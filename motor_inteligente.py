import pandas as pd
import numpy as np
import yfinance as yf
from sklearn.metrics.pairwise import cosine_similarity

def prever_com_historico(df_atual, ativo):
    try:
        # Baixa 60 dias de histórico recente direto para comparar caso o CSV não exista na nuvem
        df_hist = yf.download(ativo, period="60d", interval="1h", progress=False)
        if df_hist.empty or len(df_hist) < 120:
            return 50.0, 0
            
        precos_hist = df_hist['Close'].values
        precos_atuais = df_atual['Close'].values[-100:]
        
        if len(precos_atuais) < 100:
            return 50.0, 0
            
        padrao_atual = (precos_atuais - precos_atuais[0]) / precos_atuais[0]
        
        tamanho_janela = 100
        vetores = []
        retornos_futuros = []
        
        for i in range(len(precos_hist) - tamanho_janela - 1):
            janela = precos_hist[i : i + tamanho_janela]
            janela_norm = (janela - janela[0]) / janela[0]
            
            preco_futuro = precos_hist[i + tamanho_janela]
            preco_atual_janela = janela[-1]
            retorno = (preco_futuro - preco_atual_janela) / preco_atual_janela
            
            vetores.append(janela_norm)
            retornos_futuros.append(retorno)
            
        if len(vetores) == 0:
            return 50.0, 0
            
        vetores_hist = np.array(vetores)
        retornos_hist = np.array(retornos_futuros)
        
        similaridades = cosine_similarity([padrao_atual], vetores_hist)
        indices_top = np.argsort(similaridades[0])[-50:] # Pega os melhores matches
        resultados = retornos_hist[indices_top]
        
        sucessos = sum(1 for r in resultados if r > 0)
        score_historico = (sucessos / len(resultados)) * 100
        
        return round(score_historico, 2), len(resultados)
    except Exception as e:
        return 50.0, 0
