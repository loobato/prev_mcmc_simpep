#%% Previsao de eventos por microregiao, via os dados disponíveis

import warnings
import random
import numpy as np
import pandas as pd
from scipy.stats import norm
from mydefs import excelzar
from dados_mcmc import dados_drive

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
warnings.filterwarnings('ignore')

#%% Frequencias Microrregiao/Evento

def probs_microreg_evento(atual):
    # Função que gera uma série de multindex com as frequencias de cada evento
    # por microregiao p/ uma alocação das microrregioes nos eventos previstos
    
    m = atual.reset_index()
    if 'Data' in m.columns:
        m.drop(['Data'], axis=1, inplace=True)
    else:
        m = m[['Microrregiao','Evento']]

    # Serie de totais/microreg
    t_microreg = m.value_counts()
    
    # Serie de totais por evento
    t_ev = m.Evento.value_counts()  # Vou usar pra dividir cada linha no fim
        
    for ev in t_ev.index:
        for microreg in m.Microrregiao.unique():
            try:
                t_microreg.loc[microreg, ev] = t_microreg.loc[microreg, ev]/ t_ev[ev]
            except KeyError:

                pass

    return t_microreg.reorder_levels(['Evento', 'Microrregiao'])

def med_desv_eventos(dados_crus):
    from scipy.stats import norm
    ''' Função que tira a média e o desvio padrão dos eventos da série histórica
        e mapeia eles no dicionário map '''
    df = dados_crus['Evento'].to_frame()
    
    # Criando um mapa de nomes para numeros
    nomes = df.Evento.unique()
    numeros = np.arange(len(nomes))
    map = dict(zip(numeros, nomes))
    df = df.Evento.map(dict(zip(nomes, numeros)))

    mu = df.mean()
    std = df.std()

    return mu, std, map
    
#%% Vetor Inicial

def vetor_inicial(dds_unicos):
    dds_unicos = dds_unicos['Evento'].to_frame()
    estados = dds_unicos.Evento.unique()
    obs = dds_unicos.value_counts()
    
    vetor = pd.Series(index=estados).fillna(0)
    
    for ev in estados:
        vetor[ev] = obs[ev]
    
    vetor = vetor / obs.sum()
    
    return vetor

#%% Probabilidade de Markov

def prob_markov(n, V0, MT, trans=True):   
    # Pn = V0 . MT^n

    if trans:
        MT = np.transpose(MT)
    MTn = np.linalg.matrix_power(MT, n)

    Pn = np.matmul(MTn, V0)

    if sum(Pn) != 1.:
        Pn = Pn.round(4)
    
    return pd.Series(Pn, index=V0.index)

#%% Matriz de Transição

def watchousky(df):
    # Função de criação da matrix de transição para todo o conjunto
    
    # Lista de Eventos
    lis_ev = list(df.Evento.unique())

    # Matriz final
    matrix = pd.DataFrame(columns=lis_ev, index=lis_ev).fillna(0)
    
    # Serie de Totais
    totais = pd.Series(index=lis_ev).fillna(0)
    
    i = 1
    for ev in df.Evento:
        if totais.any():
            matrix.loc[can, ev] += 1

        if i != len(df.Evento):
            totais[ev] += 1 # Ó isso aqui está dando 1 dado a mais, pode dar merda
        else:
            pass
        can = ev
        i += 1

    for col_ev in lis_ev:
        matrix.loc[col_ev] = matrix.loc[col_ev] / totais[col_ev]
    
    return matrix

#%% Metropolis-Hasting Sampler

def met_hast_sampler(matriz, vet_inicial, dt):
    ''' Como descrito no livro 'Statistical Computing in R' '''
    from scipy.stats import norm
    
    mu, std, map = med_desv_eventos(dados_drive)
    norm(loc=mu, scale=std)

    X = list()
    prob_acc = list()
    
    # 1. Dsitribuição Proposta:
    # A dist proposta é a dist estacionária da cadeia original
    f = prob_markov(dt, vet_inicial, matriz)

    # 1.a Distribuição visada
    g = norm(loc=mu, scale=std)

    # 2. Gerar X0 de g(x)
    x0 = g.rvs()
    while round(x0) not in map.keys():
        x0 = g.rvs()

    # 3. Começar um loop
    for t in range(0, dt+1):
        if t == 0:
            x = x0
        else:
            pass
        
        # 3.a Gerar Y de g(x)
        Y = g.rvs()
        while round(Y) not in map.keys():
            Y = g.rvs()
    
        # 3.b Gerar U de Uniforme(0, 1)
        U = np.random.uniform()

        bayes = (f[map[round(Y)]]*g.pdf(x)) / (f[map[round(x)]]*g.pdf(Y))

        if bayes == 0: print('ok')
        
        # 3.c Se U <= f(y)g(x|y)/f(xt)g(y|xt) aceitar Y, e Xt+1 = Y
        # se não, Xt+1 = Xt
        alfa = min(1, bayes)

        if U <= bayes:
            x = Y
            prob_acc.append(alfa)
        else:
            p_rej = 1-alfa
            prob_acc.append(p_rej)
            pass

        X.append(map[round(x)])
    
    dis = {'Evento': X, 'Probabilidade': prob_acc}
    df = pd.DataFrame(dis)
    
    return df

#%% Alocar Microregioes

def prev_microreg(probs, mcmc):
    # Função para alocar os eventos do MHS em microrregioes de acordo com suas frequencias
    lis_microreg = list()
    copy = mcmc.copy()
    
    for ev in copy.Evento:
        loc = probs.loc[ev]
        escolha = np.random.choice(loc.index, p=loc.values)
        lis_microreg.append(escolha)
    
    try:
        copy.insert(2, 'Microrregiao', lis_microreg)
    except ValueError:
        copy.drop(columns=['Microrregiao'])
        
    return copy


#%% Substitutas de probs_microreg_evento e prev_microreg

def norms_microreg(df):
    '''Função para criar as distribuições normais de microrregioes'''

    dis_norm = dict() # dicionário com as normais de cada evento

    # puxar um conjunto de vizualizações de microrregioes por dado evento
    df = df.reset_index()
    df = df[['Microrregiao', 'Evento']].set_index(['Evento'])
 
    for ev in df.index.unique():
        dados_categoricos = df.loc[ev]

        # defino minhas categóricas e crio seus números
        var_cat = dados_categoricos.Microrregiao.unique() 
        num_cat = np.arange(len(var_cat))  
        map = dict(zip(num_cat, var_cat))

        # mapeaia os valores numéricos de volta para os dados categóricos
        dados_numericos = dados_categoricos.Microrregiao.map(dict(zip(var_cat, num_cat)))

        # Calcule a média e o desvio padrão dos dados numéricos
        mu = dados_numericos.mean()
        std = dados_numericos.std()

        # Crie uma distribuição normal usando a média e o desvio padrão
        dis_norm[ev] = (mu, std, dados_categoricos.value_counts().index, map)

    return dis_norm

def aloc_microreg(norms, prev):
    # Gere amostras aleatórias a partir da distribuição normal
    lis_microreg = []
    for ev in prev.Evento:
        mu = norms[ev][0]
        std = norms[ev][1]
        normal = norm(loc=mu, scale=std)
        amostras = normal.rvs(size=1000)  
        counts, bins = np.histogram(amostras, bins=len(norms[ev][2]))

        # Pega o lugar com maior dados gerados e associa ao dado de maior freq nos reais
        locador = dict()
        for i in range(0, len(counts)):
            con = np.sort(counts)
            serie = list(norms[ev][2])
            locador[con[-(i+1)]] = serie[i][0]

        # lista ordenada do nome de cada bin
        lis_cut = [locador[x] for x in counts]

        # alocar um valor gerado a uma bin
        rand = np.random.normal(mu, std)
        digi = np.digitize(rand, bins[1:])
        lis_microreg.append(lis_cut[digi-1])
    
    try:
        prev.insert(2, 'Microrregiao', lis_microreg)
    except ValueError:
        prev.drop(columns=['Microrregiao'])

    return prev