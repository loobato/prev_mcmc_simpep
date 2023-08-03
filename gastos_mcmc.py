#%% Previsao de gastos p/ pesquisa

import warnings
import numpy as np
import pandas as pd
from scipy.stats import norm
from dados_mcmc import precos, dados_drive
from time import time
from math import floor

warnings.filterwarnings('ignore')

#%% Distribuição de Probabilidade

def prob_item_evento(df, mapa=False): 
    ''' Função para gerar um dicionário com um mu e std individual para cada item/evento
        para que esses dados sejam usados pra criar uma distribuição normal dos itens solic'''
    from dados_mcmc import upsidedown_dis

    df = df.loc[:, ['Evento', 'Item']]

    # Contando quantos items por evento
    df_ev = df.set_index(['Evento'])

    dis = dict()
    for ev in df_ev.index.unique():
        df_it = df_ev.loc[ev]
        vcount = df_it.value_counts().index
        var_cat = [x[0] for x in vcount]

        num_cat = np.arange(len(var_cat))

        mapa = dict(zip(var_cat, num_cat))
        
        # mapeaia os valores numéricos de volta para os dados categóricos
        try:
            dados_numericos = df_it.Item.map(mapa)   
        except AttributeError:
            dados_numericos = mapa[df_it.Item]
        # Calcule a média e o desvio padrão dos dados numéricos
        mu = dados_numericos.mean()
        std = dados_numericos.std()
        dis[ev] = (mu, std, mapa)

    return dis


def prev_itens(dis, solic, ev):
    '''Função para criar uma lista categórica através de uma distribuição normal 
    das observações de itens em cada evento'''
    lis = list()
    mu, std, map = dis[ev]
    normal = norm(loc=mu, scale=std)
    amostras = normal.rvs(size=1000)  
    counts, bins = np.histogram(amostras, bins=len(map.keys()))

    # Pega o lugar com maior dados gerados e associa ao dado de maior freq nos reais
    locador = dict()
    for i in range(0, len(counts)):
        con = np.sort(counts)
        serie = list(map.keys())
        locador[con[-(i+1)]] = serie[i]
    
    # lista ordenada do nome de cada bin
    lis_cut = [locador[x] for x in counts]

    # alocar um valor gerado a uma bin
    lis_digi = list()

    for i in range(0, solic):
        rand = np.random.normal(mu, std)
        digi = np.digitize(rand, bins[1:])
        if digi == 14: digi = 13
        if digi not in lis_digi:
            lis_digi.append(digi)
        else:
            pass
    try:
        lis = [lis_cut[x] for x in lis_digi]
    except IndexError:
        pass
    return lis


def prob_pedidos(dados_crus):
    from decimal import Decimal
    ''' Função para extrair as distribuições da quantidade de pedidos que cada
        evento faz em um dicionário com valores de series, onde o idx é as qnt de 
        pedidos e os valores da serie são suas probabilidades'''

    # Dicionário com as distribuições 
    dis_ev = {}

    df = dados_crus.copy()

    # Conta quantos pedidos foram feitos pra cada ocorrencia do evento
    if 'Data' in df.columns:
        grp_ev = df.groupby(['Evento', 'Data']).count()['m']
        grp_ev.index = grp_ev.index.droplevel('Data')
    else:
        grp_ev = df.groupby(['Evento', 'Item']).count()['Microrregiao']
        grp_ev.index = grp_ev.index.droplevel('Item')

    for idx in grp_ev.index:
        para = None # Particula de controle
        mu, std = norm.fit(grp_ev.loc[idx])
        dis_ev[idx] = (mu, std)
        
    return dis_ev

#%% Gerar solicitações de itens

def solicitacoes(prob_solic, prob_item, dis, prev):
    global precos
    # Função para gerar o numero de solicitações de itens
    # Ver qual é o evento gerado e criar uma certa quantia de solicitações pra ele

    qnt_solic = []
    itens_solic = []
    lis_precos = []
    
    for ev in prev.Evento:
        solic = round(np.random.normal(prob_solic[ev][0], prob_solic[ev][1]))
        while solic < 0:
            solic = round(np.random.normal(prob_solic[ev][0], prob_solic[ev][1]))
        # tem que gerar uma lista de itens solicitados de tamanho "solic
        item = prob_item(dis, solic, ev)
        qnt_solic.append(len(item))
    
        itens_solic += [x for x in item]
    
    for i in itens_solic: lis_precos.append(precos[i])

    previsao_solicitacao = prev.loc[np.repeat(prev.index, qnt_solic)].reset_index(drop=True)
    previsao_solicitacao.insert(3, 'Item', itens_solic)
    previsao_solicitacao.insert(4, 'Valor Unitário', lis_precos)
    
    return previsao_solicitacao

#%% Df Indexado

def index_qnt(dados):
    
    df = dados.copy()
    df = df.loc[:,['Microrregiao', 'Evento', 'Item', 'Quantidade']]

    arrays = [df['Evento'] , df['Item']]
    mult = pd.MultiIndex.from_arrays(arrays)
    df = df.set_index(mult).drop(columns=['Microrregiao', 'Evento', 'Item'])

    # Correções
    df.loc[df['Quantidade'] == '100 bombonas - 5 Lt'] = 100
    df.loc[df['Quantidade'] == '1.200 bombonas – 5 lt '] = 1200
    df = df.astype('int64')
    df = df.reset_index()
    df = df.drop(['Evento'], axis=1).set_index(['Item'])

    parametros = dict()
    for conj in df.index.unique():
        quantidades = df.loc[conj, 'Quantidade']
        
        # Achar a media e std dos dados em uma Normal
        mu, std = norm.fit(quantidades)
        parametros[conj] = (mu, std)

    return df, parametros
 
# %% Estimar Quantidades

def est_quantidades(df_previsao, df_indexado):
    '''Função para estimar as quantidades solicitadas de cada item'''

    prev = df_previsao.copy()
    indexado = df_indexado.copy()
    lis = list()    # lista dos dados gerados

    # Criar o dicionário com os parâmetros da distribuição
    parametros = dict()
    for conj in indexado.index.unique():
        quantidades = indexado.loc[conj, 'Quantidade']
        
        # Achar a media e std dos dados em uma Normal
        mu, std = norm.fit(quantidades)
        parametros[conj] = (mu, std)

    # Parametro de suavização
    alfa = 0.7

    for itens in prev['Item']:
        P = False
        
        mu = parametros[itens][0]
        std = parametros[itens][1]

        while not P:
            # Gera um valor entre 0 e 1
            val_uniforme = np.random.uniform()

            # Transformar o valor selecionado para a Normal
            val_normal = norm.ppf(val_uniforme)

            # Transformar o valor de volta
            val_transformado = (val_normal * std + mu)*alfa # como colocar isso no artigo

            if val_transformado < 0:
                pass
            elif 0 <= val_transformado <= 1:
                val_transformado = 1
                lis.append(val_transformado)
                P = True
            else:
                val_transformado = floor(val_transformado)
                lis.append(val_transformado)
                P = True

    prev['Quantidade'] = lis

    return prev

#%% Valores totais

def totais(df_previsao):
    '''Função para calcular os valores totais previstos e esperados'''
    
    prev = df_previsao.copy()

    # Valor Total
    prev['Valor Total'] = prev['Valor Unitário'] * prev['Quantidade']

    # Valor Esperado
    prev['Valor Esperado'] = prev['Valor Unitário'] * prev['Quantidade'] * prev['Probabilidade']
    
    prev = prev.round({'Probabilidade':4, 'Valor Total':2, 'Valor Esperado':2})

    return prev
