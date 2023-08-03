#%%
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

class Grafico():
    def __init__(self) -> None:
        self.path = r"C:\Users\henri\OneDrive\Desktop\Cousas da Facu\Pesquisa\Projeto IC\plots\artigo"
        pass
    
    def evento(self, real, previsao, save=False):
        vc_prev = previsao.Evento.sort_values()
        vc_real = real.Evento.reset_index(drop=True).sort_values()
        indices = vc_real.unique()
        indices[0] = 'Chuvas\nIntensas'
        vc_prev = vc_prev.replace(vc_prev.unique(), np.arange(7))
        vc_real = vc_real.replace(vc_real.unique(), np.arange(7))

        fig, ax = plt.subplots(1, 1, figsize=(9, 6))
        hist = ax.hist([vc_prev.values, vc_real.values], 7, align='mid', label=['Previsto', 'Real'], density=True)
        ax.legend()
        plt.xticks([x + 0.4 for x in hist[1][:-1]], indices)
        plt.ylabel('Freq.')
        plt.title('Densidade de Eventos')
        plt.gcf().autofmt_xdate()
        plt.tight_layout()
        if save: fig.savefig(self.path+'\eventos.png')
        
        return fig
        
    def microrregiao(self, real, previsao, save=False):
        gp_real = real.groupby(['Evento', 'Microrregiao']).count().sort_index()
        gp_prev = previsao.groupby(['Evento', 'Microrregiao']).count().sort_index()

        serie_real = pd.Series(index=gp_real.index)
        for ev, mc in gp_real.index:
            total = gp_real.loc[ev].sum().values[0]
            count_mc = gp_real.loc[ev, mc].values[0]
            serie_real[(ev,mc)] = count_mc / total
        gp_real['densidade'] = serie_real

        serie_prev = pd.Series(index=gp_prev.index)
        for ev, mc in gp_prev.index:
            total = gp_prev.loc[ev].sum().values[0]
            count_mc = gp_prev.loc[ev, mc].values[0]
            serie_prev[(ev,mc)] = count_mc / total
        gp_prev['densidade'] = serie_prev
        alt_ev = None
        for ev, mc in gp_real.index:
            if ev == alt_ev:
                pass
            else:
                fig, ax = plt.subplots(1,1)
                por_evento_real = gp_real.loc[ev, 'densidade'].sort_index()
                por_evento_prev = gp_prev.loc[ev, 'densidade']
                
                for idx in por_evento_real.index:
                    try:
                        por_evento_prev.loc[idx]
                    except KeyError:
                        por_evento_prev.loc[idx] = 0

                por_evento_prev.sort_index(inplace=True)
                
                ax.barh(por_evento_real.index, por_evento_real.values, 0.4, label='Real')
                ax.barh([x - 0.4 for x in np.arange(len(por_evento_real.index))], por_evento_prev.values, 0.4, label='Previsto')
                
                ax.set_xlabel('Freq.')
                ax.set_ylabel('Microrregião')
                plt.yticks([x-0.2 for x in np.arange(len(por_evento_real.index))])
                plt.title(ev)
                plt.legend()
                plt.gcf().autofmt_xdate()
                plt.tight_layout()
                if save: fig.savefig(self.path+f'\microrregiao_{ev}.png')

            alt_ev = ev
        
        return fig

    def solicitacoes(self, real, previsao, save=False):
        # gpby real
        grp_real = real.groupby(['Evento', 'Data']).count()['m']
        grp_real.index = grp_real.index.droplevel('Data')

        # gpby prev
        # criar um identificador pra cada evento
        serie = pd.Series(index=previsao.index)
        i = 0
        can_ev, can_prob, can_mc = None, None, None
        for idx in previsao.index:
            row = previsao.loc[idx]
            ev, prob, mc = row['Evento'], row['Probabilidade'], row['Microrregiao']
            if ev == can_ev and prob == can_prob and mc == can_mc: 
                serie[idx] = i
            else:
                i += 1
                serie[idx] = i
            can_ev, can_prob, can_mc = ev, prob, mc
        previsao['identificador'] = serie
        grp_prev = previsao.groupby(['Evento', 'identificador']).count()['Item']
        grp_prev.index = grp_prev.index.droplevel(1)

        # criar um grafico onde o x são os eventos e o y é a média de solicitacoes
        serie_real = pd.Series()
        serie_prev = pd.Series()
        for ev in grp_real.index:
            mu_real = grp_real.loc[ev].mean()
            mu_prev = grp_prev.loc[ev].mean()
            if ev == 'Chuvas Intensas':
                ev = 'Chuvas\nIntensas'
            serie_real[ev] = mu_real
            serie_prev[ev] = mu_prev

        fig, ax = plt.subplots(1, 1)
        ax.bar(serie_real.index, serie_real.values, 0.4, label='Real')
        ax.bar([x + 0.4 for x in np.arange(len(serie_prev.index))], serie_prev.values, 0.4, label='Previsto')
        ax.set_xlabel('Evento')
        ax.set_ylabel('Média')
        plt.xticks([x + 0.2 for x in np.arange(len(serie_prev.index))], fontsize=9.5)
        plt.legend()
        plt.title('Média de Solicitações')
        plt.gcf().autofmt_xdate()
        plt.tight_layout()
        if save: fig.savefig(self.path + '\solicitacoes.png')
        
        return fig
    
    def quantidades(self, real, previsao, save=False):
        # grby real -> já é o real
        # grby prev
        arrays = [previsao['Evento'], previsao['Item']]
        mult = pd.MultiIndex.from_arrays(arrays)
        grp_prev = previsao.set_index(mult)['Quantidade']
        grp_prev = grp_prev.droplevel(0)

        serie_real = pd.Series()
        serie_prev = pd.Series()
        for item in real.index.unique():
            mu_real = real.loc[item].mean()
            try:
                mu_prev = grp_prev.loc[item].mean()
            except KeyError:
                mu_prev = 0
            serie_real[item] = mu_real.values[0]
            serie_prev[item] = mu_prev

        serie_real.sort_index(inplace=True)
        serie_prev.sort_index(inplace=True)

        fig, ax = plt.subplots(1, 1)
        ax.barh(serie_real.index, serie_real.values, 0.4, label='Real')
        ax.barh([x - 0.4 for x in np.arange(len(serie_real.index))], serie_prev.values, 0.4, label='Previsto')
        ax.set_xscale('log')
        ax.set_ylabel('Itens')
        ax.set_xlabel('Média (escala logarítmica)')
        plt.legend()
        plt.title('Média de quantidades solicitadas')
        plt.gcf().autofmt_xdate()
        plt.tight_layout()
        if save: fig.savefig(self.path + '\quantidades.png')
        
        return fig

    def itens(self, real, previsao, save=False):
        grp_real = real.groupby(['Evento', 'Item']).count()['Microrregiao']
        grp_prev = previsao.groupby(['Evento', 'Item']).count()['Microrregiao']

        # formando densidades (series multindex)
        serie_real = pd.Series(index=grp_real.index)
        for ev, it in grp_real.index:
            total = grp_real.loc[ev].sum()
            count_mc = grp_real.loc[ev, it]
            serie_real[(ev,it)] = count_mc / total

        serie_prev = pd.Series(index=grp_prev.index)
        for ev, it in grp_prev.index:
            total = grp_prev.loc[ev].sum()
            count_mc = grp_prev.loc[ev, it]
            serie_prev[(ev,it)] = count_mc / total

        alt_ev = None
        for ev, it in serie_real.index:
            if ev == alt_ev:
                pass
            else:
                fig, ax = plt.subplots(1, 1)
                por_evento_real = serie_real.loc[ev]
                por_evento_prev = serie_prev.loc[ev]

                for idx in por_evento_real.index:
                    try:
                        por_evento_prev.loc[idx]
                    except KeyError:
                        por_evento_prev.loc[idx] = 0

                for idx in por_evento_prev.index:
                    try:
                        por_evento_real.loc[idx]
                    except KeyError:
                        por_evento_real.loc[idx] = 0

                por_evento_real.sort_index(inplace=True)
                por_evento_prev.sort_index(inplace=True)

                ax.barh(por_evento_real.index, por_evento_real.values, 0.4, label='Real')
                ax.barh([x - 0.4 for x in np.arange(len(por_evento_real.index))], por_evento_prev.values, 0.4, label='Previsto')
                ax.set_ylabel('Item')
                ax.set_xlabel('Freq.')
                plt.yticks([x-0.2 for x in np.arange(len(por_evento_real.index))])
                plt.legend()
                plt.title(f'{ev}')
                plt.gcf().autofmt_xdate()
                plt.tight_layout()
                if save: fig.savefig(self.path+f'\item_{ev}.png')
            
            alt_ev = ev
        
        return fig
#%%
