#%%
import time
import numpy as np
import pandas as pd
import scipy.stats as stats
import eventos_mcmc as ev
import gastos_mcmc as gt
import dados_mcmc as ds
import scorador as sc
from dados_mcmc import dados_drive
from mydefs import excelzar
from graficos import Grafico

np.random.seed(49)

# Dados
dados_indexados = ds.sep_microreg_data(dados_drive)         
dados_unicos = ds.eventos_unicos(dados_indexados)           
dados_gastos = dados_drive.dropna(axis=0, subset=['Item'])  # Corregção de dados
indexado, qnts_msm = gt.index_qnt(dados_gastos)             # Quantidades de itens solicitados
                                                            # e o msmi de quantidades
# Probabilidades 
v0 = ev.vetor_inicial(dados_unicos)
m = ev.watchousky(dados_unicos)
tup_sc_evs = ev.med_desv_eventos(dados_drive)               # mu, std e map dos eventos
norm_microreg = ev.norms_microreg(dados_unicos)             # m, s e map(em[3]) de microreg/evento
msm = gt.prob_item_evento(dados_gastos)                     # mu e std e map de item/evento
pri = gt.prev_itens
ppd = gt.prob_pedidos(dados_drive)                          # m,std da quantidade de pedidos que cada evento

#%%

try:
    n_testes = int(input('n previsoes:  '))
except ValueError:
    n_testes = 1

# Loop de criação
lis_test = []
Inicio = time.time()
Df_Erros = pd.DataFrame(columns=['Evento', 'Microrregiao', 'Itens', 'Solicitacoes', 'Quantidades','Média total'])
Dis_Previsoes = dict()

for i in range(1, n_testes+1):
    # loop para realizar varios testes e tirar seus EMAP e entao realizar um teste de hipotese sobre esses erros

    inicio = time.time()

    # Previsões
    previsao_eventos = ev.met_hast_sampler(m, v0, 319)                              # Previsão de eventos via mhs
    previsao_microrregiao = ev.aloc_microreg(norm_microreg, previsao_eventos)       # Previsão de microrregiao dada a dist de prob de cada microreg em cada evento
    previsao_solicitacao = gt.solicitacoes(ppd, pri, msm, previsao_microrregiao)    # Pev de solicitações e de itens de acordo com as 
    previsao_quantidades = gt.est_quantidades(previsao_solicitacao, indexado)
    previsao = gt.totais(previsao_quantidades)

    # Scores
    parametros_previsao = {'evento': sc.score_evento(previsao, tup_sc_evs),
                        'microrregiao': sc.score_microrregiao(previsao_microrregiao, {y:(x[0], x[1], x[3]) for y, x in norm_microreg.items()}),
                        'itens': sc.score_itens(previsao_solicitacao, msm),
                        'solicitacoes': sc.score_solicitacoes(previsao_solicitacao, ppd),
                        'quantidades': sc.score_quantidades(previsao_quantidades, qnts_msm)}

    # Erros de cada previsão
    df_emp = sc.scorador(parametros_previsao)
    lis_test.append(df_emp['Média total'].values[0])
    Df_Erros = pd.concat([Df_Erros, df_emp], ignore_index=True)

    # Guardar a previsao
    Dis_Previsoes[f'Prev. {i}'] = previsao

    fim = time.time()

    print(f'{i}/{n_testes}')
    print(f'Tempo de exec. da previsão {i}:\t{fim-inicio:.2f}s')
    print(f'Tempo de exec. até agora:\t{fim-Inicio:.2f}s')

Fim = time.time()   
print(f'Tempo total:\t{Fim-Inicio:.2f}s')

Df_Erros.index.name = 'Previsões'       # colocando nome boniitn
Df_Erros = Df_Erros / 100               # ajeitando pra colocar em porcentagem no excel

dis_erro = Df_Erros.to_dict()


print(f'Erro Total: {Df_Erros["Média total"].mean()*100:.2f}%')

# %% Graficos

graf = Grafico()
graf.evento(dados_unicos, previsao_eventos, save=False)
graf.microrregiao(dados_unicos.reset_index(),previsao_microrregiao,save=False)
graf.itens(dados_gastos, previsao_solicitacao, save=False)
graf.solicitacoes(dados_drive, previsao_solicitacao, save=False)
graf.quantidades(indexado, previsao_quantidades, save=False)


# %%
