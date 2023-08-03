#%%
import numpy as np
import pandas as pd
import eventos_mcmc as ev
import gastos_mcmc as gt
import matplotlib.pyplot as plt
from scipy.stats import norm
from sklearn.metrics import mean_absolute_percentage_error
from dados_mcmc import dados_drive, upsidedown_dis

#%% Score de eventos previstos

def score_evento(prev, msmi):
    from scipy.stats import norm
    
    mui, stdi, mapa = msmi
    mapa = upsidedown_dis(mapa)
    try:
        vals = prev[f'Evento'].map(mapa)
    except:
        pass
    muf, stdf = norm.fit(vals)

    dis = {'med':{'i':mui, 'f':muf}, 'std':{'i':stdi, 'f':stdf}}

    return dis

#%% Score de Microrregioes alocadas

def score_microrregiao(prev, dis_inicial):
    ''' Função que da um dicionário com a média i e f e o std i e f
        da previsão de microrregioes'''

    prev = prev[['Evento', 'Microrregiao']].set_index('Evento')
    dis = dict()
    for evento in prev.index.unique():
        mui, stdi, mapa = dis_inicial[evento]
        seq = prev.loc[evento].replace(upsidedown_dis(mapa))
        muf, stdf = norm.fit(seq.values)
        dis[evento] = {'med':{'i':mui, 'f':muf}, 'std':{'i':stdi, 'f':stdf}}

    return dis

#%% Score de Solicitações feitas

def score_itens(prev, msmi):
    # dicionário de mi, std e mapa FINAL dos eventos por cada item
    msmf = gt.prob_item_evento(prev, msmi)
    dis = dict()
    for evento in prev.Evento.unique():
        mui, stdi = msmi[evento][0], msmi[evento][1]
        muf, stdf = msmf[evento][0], msmf[evento][1]

        dis[evento] = {'med':{'i':mui, 'f':muf}, 'std':{'i':stdi, 'f':stdf}}

    return dis

def score_solicitacoes(prev, msmi):
    # dicionário de mi, std e mapa FINAL dos eventos por cada item
    msmf = gt.prob_pedidos(prev)
    dis = dict()
    for evento in prev.Evento.unique():
        mui, stdi = msmi[evento][0], msmi[evento][1]
        muf, stdf = msmf[evento][0], msmf[evento][1]

        dis[evento] = {'med':{'i':mui, 'f':muf}, 'std':{'i':stdi, 'f':stdf}}
    return dis

#%% Score de Quantidades

def score_quantidades(prev, msmi):
    idex, msmf = gt.index_qnt(prev)

    dis = dict()
    for evento in prev.Item.unique():
        mui, stdi = msmi[evento][0], msmi[evento][1]
        muf, stdf = msmf[evento][0], msmf[evento][1]

        dis[evento] = {'med':{'i':mui, 'f':muf}, 'std':{'i':stdi, 'f':stdf}}
    return dis

#%% Score final

def scorador(par_prev):
    ''' Funcao que gera uma normal com o mu e std da previsao e tira o
        erro médio absoluto percentual de cada conjunto'''
    df = pd.DataFrame(columns=[f'{x.capitalize()}' for x in par_prev.keys()])

    for k in par_prev.keys():
        if k == 'evento':
            parametros = par_prev[k]
            normal_inicial = norm(loc=parametros['med']['i'], scale=parametros['std']['i'])
            normal_final = norm(loc=parametros['med']['f'], scale=parametros['std']['f'])

            i = normal_inicial.rvs(1000)
            f = normal_final.rvs(1000)

            erro_abs = mean_absolute_percentage_error(i, f)
            
            df.loc[0, k.capitalize()] = erro_abs
            
        else:
            tipos = par_prev[k]
            med_tipos = np.array([])
            for nome in tipos.keys():
                normal_inicial = norm(loc=tipos[nome]['med']['i'], scale=tipos[nome]['std']['i'])
                normal_final = norm(loc=tipos[nome]['med']['f'], scale=tipos[nome]['std']['f'])

                i = normal_inicial.rvs(1000)
                f = normal_final.rvs(1000)

                erro_abs = mean_absolute_percentage_error(i, f)
                med_tipos = np.append(med_tipos, erro_abs)
            df[k.capitalize()] = med_tipos.mean()

    df['Média total'] = df.values.mean()

    return df

#%% Gráficos

