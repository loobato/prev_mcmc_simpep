#%% Dados para os códigos

import numpy as np
import pandas as pd
import warnings
from mydefs import excelzar

warnings.filterwarnings('once')

#%% Dados - 2013 a 2019
path = 'dds-drive.xlsx'
dados_drive1 = pd.read_excel(path, sheet_name='Eventos (2013-2019)')

dados_drive1 = dados_drive1.drop(labels=['Código', 'Fornecedor', 'Mes', 'Ano', 'Data Entrega',], axis=1)
dados_drive1 = dados_drive1.dropna(subset=['m', 'Microrregiao', 'Evento', 'Data'])

# Renomeando
dados_drive1.Evento.replace({'enxurradas':'Enxurrada', 'fortes chuvas': 'Chuvas Intensas', 
                            'Fortes Chuvas': 'Chuvas Intensas', 'cheias dos rios ':'Cheia dos Rios',
                            'fortes chuvas ': 'Chuvas Intensas', 'Enxurradas':'Enxurrada',
                            'enxurrada':'Enxurrada', 'VENDAVAL':'Vendaval', 'vendaval ':'Vendaval',
                            'vendaval':'Vendaval', 'Tempestade/Granizo': 'Granizo', 'Alagamento':'Inundação',
                            'Alagamentos': 'Inundação', 'Enchentes': 'Inundação'}, inplace=True)
dados_drive1.Microrregiao.replace({'S.Miguel Oeste':'São Miguel do Oeste'}, inplace=True)

# Drops de Eventos não-relacionados
drop_estoque = list(dados_drive1.loc[dados_drive1['Evento'] == 'Estoque'].index)
dados_drive1 = dados_drive1.drop(index=drop_estoque)
drop_acordo = list(dados_drive1.loc[dados_drive1['Evento'] == 'Acordo '].index)
dados_drive1 = dados_drive1.drop(index=drop_acordo)
drop_tornado = list(dados_drive1.loc[dados_drive1['Evento'] == 'Tornado'].index)
dados_drive1 = dados_drive1.drop(index=drop_tornado)
drop_cheia = list(dados_drive1.loc[dados_drive1['Evento'] == 'Cheia dos Rios'].index)
dados_drive1 = dados_drive1.drop(index=drop_cheia)

#%% Dados - 2020 a 2023
path2 = 'dds-defcivil-2020_2023.xlsx'
dados_drive2 = pd.read_excel(path2, sheet_name='PEDIDOS')

dados_drive2 = dados_drive2.drop(labels=[' ', 'Coordenador Regional', 'Nº Oficio GEASH', 'SGPE',
                                         'Origem dos itens a serem entregues', 'Data de Liberação',
                                         'Fornecedor'], axis=1)
dados_drive2 = dados_drive2.dropna()

# Mudando dtypes
drop_index = [dados_drive2.loc[dados_drive2['Data do Decreto'] == '22/12/0201'].index, dados_drive2.loc[dados_drive2['Valor unitário'] == 'R$ 2.600,00'].index]
dados_drive2 = dados_drive2.drop(index=drop_index[0])
dados_drive2 = dados_drive2.drop(index=drop_index[1])
dados_drive2['Data do Decreto'] = pd.to_datetime(dados_drive2['Data do Decreto'], dayfirst=True)
dados_drive2['Valor unitário'] = dados_drive2['Valor unitário'].astype('float64')

# Renomeando
dados_drive2.Evento.replace({'Chuva de junho':'Chuvas Intensas', 'Chuvas de Maio':'Chuvas Intensas',
                             'Chuvas Out22':'Chuvas Intensas', 'Chuvas Nov 22':'Chuvas Intensas',
                             'Chuvas Dez 22':'Chuvas Intensas', 'Chuva Jan.23':'Chuvas Intensas',
                             'Chuva fev. 23':'Chuvas Intensas', 'Granizo ':'Granizo',
                             'Ventos Costeiros ':'Vendaval', 'Inudação ':'Inundação', 'Ciclone Ago':'Ciclone'}, inplace=True)

# Organizando o DF
dados_drive2 = dados_drive2[['Município', 'COREDEC', 'Evento', 'Produtos ', 'Data do Decreto', 'Valor unitário', 'Quantidade', 'Valor Total']]
dados_drive2.columns = dados_drive1.columns

#%% Ajuste de itens

def replace_itens():
    global dados_drive, dados_drive2
    itens_finais = dados_drive2['Item'].unique()

    tratar_itens = pd.Series(dados_drive.Item.unique())
    tratar_itens = tratar_itens.dropna()

    dis_alt_item = {}

    for item_chave in tratar_itens:
        item = item_chave.lower().strip()
        palavras = item.split()
        
        # Tratar kits e telhas
        if 'kit' in item or 'telha' in item:
            palavras[0] = palavras[0].removesuffix('s')
        # Tratar e já mapear as águas
        elif 'água' in item:
            dis_alt_item[item_chave] = 'Água potável'
            pass
        # Tratar colchões
        elif 'ões' in item:
            palavras[0] = 'colchão'
        # Tratar cestas
        elif 'cesta' in item:
            dis_alt_item[item_chave] = 'Cesta básica 7d'
            pass
        # Tratar pregos
        elif palavras[0] == 'prego':
            dis_alt_item[item_chave] = 'Prego 4mm'
        # Tratar parafusos
        elif palavras[0] == 'parafuso':
            dis_alt_item[item_chave] = 'Parafuso 5mm e 6mm'

        # Tratar kit acomodação (esse kit foi avaliado que se trata de acomodações de casal)
        # Cobertores são de casal
        if 'acomodação' in palavras[-1] or 'cobertores' in palavras[0]:
            dis_alt_item[item_chave] = 'Kit aco casal'
        # Tipos demais de telhas, agrupando-os aqui em telha 4mm
        elif 'telha' in palavras[0]:
            dis_alt_item[item_chave] = 'Telha 4mm'
        elif 'humanitária' in item:
            dis_alt_item[item_chave] = 'Cesta básica 7d'

        for correcao in itens_finais:
            palavras_dds2 = correcao.lower().split()

            # Teste de primeira e última palavra
            if palavras[0] in palavras_dds2[0] or palavras_dds2[0] in palavras[0]:
                if palavras[0] == 'colchão' and len(palavras)==1:
                    dis_alt_item[item_chave] = 'Colchão Solteiro'
                
                if palavras[-1] in palavras_dds2[-1] and item_chave not in dis_alt_item.keys():                    
                    dis_alt_item[item_chave] = correcao
                elif palavras_dds2[-1] in palavras[-1]:
                    dis_alt_item[item_chave] = correcao
                elif 'higiene' in item and 'higiene' in correcao:
                    dis_alt_item[item_chave] = correcao
                elif 'limpeza' in item and 'limpeza' in correcao:
                    dis_alt_item[item_chave] = correcao
                    
                else:
                    None
            
            else:
                # O que cai em Outros são lonas e ripas de madeiras, os quais tem um valor diferente
                # nos dados atuais, ou não tem informação de valor nos dados atuais
                if item_chave not in dis_alt_item.keys():
                    dis_alt_item[item_chave] = 'Outros'

    dis_alt_item['Reserv. 5 mil L'] = 'Reserv. 5 mil L'
    dis_alt_item['Reserv. 10 mil L'] = 'Reserv. 10 mil L'
    dis_alt_item['Reserv. 15 mil L'] = 'Reserv. 15 mil L'
    dis_alt_item['Reserv. 20 mil L'] = 'Reserv. 20 mil L'

    return dis_alt_item

#%% Separar por ocorrencias
def sep_microreg_data(df):
    # Função para separar os dados por microregiao e data em MultIndex
    
    arrays = [df['Microrregiao'], df['Data']]
    mult = pd.MultiIndex.from_arrays(arrays, names=['Microrregiao', 'Data'])
    df = df.drop(['Microrregiao', 'Data'], axis=1)
    df = df.set_index(mult).sort_index()

    return df

def eventos_unicos(df):
    # Função para separar por microreg e data os eventos sem duplicatas
    
    df = df.Evento
    DIS = {'Evento':list()}
    
    for idx in df.index.unique():
        DIS['Evento'].append(df.loc[idx][0])

    DF = pd.DataFrame(DIS, index=df.index.unique())
        
    return DF 

#%% Auxiliares

def upsidedown_dis(dis):
    '''Inverter dicionário'''
    dis_invertido = {valor: chave for chave, valor in dis.items()}
    return dis_invertido


#%% Variavel de Precos

precos = pd.read_excel(path2, 'ARP')
precos = precos.drop(index=[0, 2], columns=['FORNECEDOR', 'DESCRIÇÃO', 'POSIÇÃO DE ESTOQUE', 'SGPe', 'STATUS'])
precos = precos.iloc[:29].dropna().reset_index(drop=True)
precos = precos.set_index(['ITENS'])['VALOR UNITÁRIO']
precos['Outros'] = 156.209

#%% Concatenando e deixando tudo bonitin

dados_drive = pd.concat([dados_drive1, dados_drive2])
dados_drive = dados_drive.sort_values(by='Data', axis=0).reset_index(drop=True)
dados_drive.Item.replace(replace_itens(), inplace=True)

#%% Save

