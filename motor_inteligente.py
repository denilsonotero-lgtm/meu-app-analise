import pandas as pd
import numpy as np
import os

try:
    from sklearn.metrics.pairwise import cosine_similarity
    has_sklearn = True
except ImportError:
    has_sklearn = False

def carregar_e_normalizar(ativo):
    filename = f'base_historica/{ativo.replace("=", "_").replace(".", "_")}.csv'
    if not os.path.exists(filename):
        return None
    
    try:
        df = pd.read_csv(filename)
        if 'Close' not in df.columns:
            return None
        
        precos = df['Close'].values
        if len(precos) < 120:
            return None
            
        tamanho_janela = 100
        vetores = []
        retornos_futuros = []
        
        for i in range(len(precos) - tamanho_janela - 1):
            janela = precos[i : i + tamanho_janela]
            janela_norm = (janela - janela[0]) / janela[0]
            
            preco_futuro = precos[i + tamanho_janela]
            preco_atual_janela = janela[-1]
            retorno = (preco_futuro - preco_atual_janela) / preco_atual_janela
            
            vetores.append(janela_norm)
            retornos_futuros.append(retorno)
            
        return np.array(vetores), np.array(retornos_futuros)
    except:
        return None

def prever_com_historico(df_atual, ativo):
    if not has_sklearn:
        return 50.0, 0
        
    precos_atuais = df_atual['Close'].values[-100:]
    if len(precos_atuais) < 100:
        return 50.0, 0
        
    padrao_atual = (precos_atuais - precos_atuais[0]) / precos_atuais[0]
    
    dados_hist = carregar_e_normalizar(ativo)
    if dados_hist is None:
        return 50.0, 0
        
    vetores_hist, retornos_hist = dados_hist
    
    similaridades = cosine_similarity([padrao_atual], vetores_hist)
    indices_top = np.argsort(similaridades[0])[-300:]
    resultados = retornos_hist[indices_top]
    
    sucessos = sum(1 for r in resultados if r > 0)
    score_historico = (sucessos / len(resultados)) * 100
    
    return round(score_historico, 2), len(resultados)
