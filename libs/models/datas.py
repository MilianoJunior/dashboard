from libs.utils.decorators import desempenho, get_error
from libs.models.db import Database
from libs.models.calculos import calcular_energia_acumulada
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import numpy as np
from libs.utils.db_utils import init_db_connection
import re

@desempenho
def parse_query_info(query: str) -> dict:
    """
    Extrai colunas, data_inicial e data_final de uma query SQL padrão.
    Retorna um dicionário com as chaves: colunas (list), data_inicial (str), data_final (str), tabela (str).
    """
    # Extrai colunas
    colunas_match = re.search(r'SELECT\s+(.*?)\s+FROM', query, re.IGNORECASE)
    colunas = [c.strip() for c in colunas_match.group(1).split(',')] if colunas_match else []
    # Extrai tabela
    tabela_match = re.search(r'FROM\s+([\w\d_]+)', query, re.IGNORECASE)
    tabela = tabela_match.group(1) if tabela_match else ''
    # Extrai datas
    datas_match = re.search(r"data_hora\s+BETWEEN\s+'([^']+)'\s+AND\s+'([^']+)'", query, re.IGNORECASE)
    data_inicial = datas_match.group(1) if datas_match else None
    data_final = datas_match.group(2) if datas_match else None
    return {
        'colunas': colunas,
        'tabela': tabela,
        'data_inicial': data_inicial,
        'data_final': data_final
    }

@desempenho
def tratamento_df(df_: pd.DataFrame) -> pd.DataFrame:
    for col in df_.dtypes.index:
        if df_[col].dtype != 'int64' and df_[col].dtype != 'float64' and col != 'data_hora':
            if pd.to_numeric(df_[col], errors='coerce').notna().all():
                df_[col] = df_[col].astype(float)
                df_[col] = df_[col].fillna(0)
        colunas_numericas = df_.select_dtypes(include=[np.number]).columns
        mask = (df_[colunas_numericas] >= 0).all(axis=1)
    
        df_ = df_[mask]
    return df_

@desempenho
def get_db_data(data_inicial, data_final):
    table = st.session_state['usina']['tabela']
    data_inicial = data_inicial or (datetime.now() - timedelta(days=240)).strftime('%Y-%m-%d %H:%M:%S')
    data_final = data_final or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def build_columns(energia, nivel):
        return ', '.join(f'{v} as {k}' for d in [energia, nivel] for k, v in d.items())
    
    def fetch_and_process(table_name, energia, nivel, is_multi=False):
        colunass = build_columns(energia, nivel)
        query = f'select {colunass} from {table_name} where data_hora >= "{data_inicial}" and data_hora <= "{data_final}"'
        # print('query: ', query)
        result = st.session_state['db'].fetch_data(query)
        df = pd.DataFrame(result)
        df = tratamento_df(df)
        if is_multi:
            df['data_hora'] = df['data_hora'].dt.round('min')
        #     print('Tabela: ', table_name)
        #     print('1 values: ', df.values[0])
        #     print('2 values: ', df.values[-1])
        #     print('--------------------------------')
        # print('df.columns: ', df.columns)
        # print('df.shape: ', df.shape)
        return df
    
    if isinstance(table, str):
        energia = st.session_state['usina']['energia']
        nivel = st.session_state['usina']['nivel']
        df_ = fetch_and_process(table, energia, nivel)
    else:
        df_list = [fetch_and_process(table[key], st.session_state['usina']['energia'][key],
                                     st.session_state['usina']['nivel'][key], is_multi=True)
                   for key in table]
        df_ = pd.merge(df_list[0], df_list[1], on='data_hora', how='outer')
        # print('df_.columns: ', df_.columns)
        # print('df_.shape: ', df_.shape)
    
    st.session_state['dados'] = df_
    

@desempenho
def get_info_usina(comando: str) -> str:
    try:
        # energia = ', '.join(st.session_state['usina']['energia'].values())
        cols_energia = st.session_state['usina']['cols_energia']
        cols_nivel = st.session_state['usina']['cols_nivel']
        # nivel = ', '.join(st.session_state['usina']['nivel'].values())
        data_inicial = datetime.now() - timedelta(days=30)
        data_inicial_180 = datetime.now() - timedelta(days=180)
        data_final = datetime.now()
        data_inicial_nivel = datetime.now() - timedelta(hours=1)
        data_final_nivel = datetime.now()
        # f"SELECT {', '.join(colunas_selecionadas)} FROM {usina['tabela']} WHERE data_hora BETWEEN '{data_hora_inicial}' AND '{data_hora_final}'"
        comandos = {
            'energia total': f"SELECT {cols_energia} FROM {st.session_state['usina']['tabela']} ORDER BY data_hora DESC LIMIT 1",
            'energia total 30 dias': f"SELECT {cols_energia} FROM {st.session_state['usina']['tabela']} WHERE data_hora BETWEEN '{data_inicial}' AND '{data_final}'",
            'energia total 180 dias': f"SELECT {cols_energia} FROM {st.session_state['usina']['tabela']} WHERE data_hora BETWEEN '{data_inicial_180}' AND '{data_final}'",
            'describe nivel': f"SELECT {cols_nivel} FROM {st.session_state['usina']['tabela']} ORDER BY data_hora DESC LIMIT 60",
            'nivel': f"SELECT {cols_nivel} FROM {st.session_state['usina']['tabela']} WHERE data_hora BETWEEN '{data_inicial_nivel}' AND '{data_final_nivel}'",
            'nome colunas': f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{st.session_state['usina']['tabela']}'",
            'describe temperatura': f"SELECT * FROM {st.session_state['usina']['tabela']} ORDER BY data_hora DESC LIMIT 120",
        }
        if comando not in comandos:
            raise ValueError(f"Comando '{comando}' não encontrado")
        return comandos[comando]
    except Exception as e:
        get_error('get_info_usina, ln 155', e)

@desempenho
def get_ultimos_180_dias_mensal() -> pd.DataFrame:
    try:
        # query = get_info_usina('energia total 180 dias')
        get_db_data(data_inicial=None, data_final=None)
        df = st.session_state['dados']
        st.session_state['ultima_atualizacao'] = df['data_hora'].iloc[-1]


        cols_energia = st.session_state['usina']['cols_energia'].split(',')
        df = df[cols_energia]
        data = calcular_energia_acumulada(df, cols_energia, 'M')
        data = data.reset_index()
        
        # Criar coluna com mês/ano em português
        meses_pt = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
        def mes_ano_pt(ano_mes):
            if isinstance(ano_mes, str):
                ano, mes = ano_mes.split('-')
            else:
                ano = ano_mes.year
                mes = f"{ano_mes.month:02d}"
            return f"{meses_pt[int(mes)-1]}/{ano}"
        
        # Detectar nome da coluna do index
        idx_col = data.columns[0]
        data['data_hora'] = data[idx_col].apply(mes_ano_pt)
        data.drop(0, inplace=True)
        # st.write('data: ',data)
        return data
    except Exception as e:
        get_error('get_ultimos_180_dias_mensal, ln 205', e)


@desempenho
def get_data_card_energia() -> dict:
    try:
        ultimos_180_dias = get_ultimos_180_dias_mensal()
        colunas_mensal = [col for col in ultimos_180_dias.columns if 'prod_' in col]
        ultimos_180_dias['total'] = ultimos_180_dias[colunas_mensal].sum(axis=1)
        ultimos_180_dias['percentual'] = ultimos_180_dias['total'].pct_change(periods=1) * 100
        ultimos_180_dias = ultimos_180_dias[::-1]
        ultima_atualizacao = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        if 'last_update' not in st.session_state:
            st.session_state.last_update = ultima_atualizacao
        list_cards = {}
        for index, linha in ultimos_180_dias.iterrows():
            mes = f'{linha["data_hora"]}'
            name_col = f'Geração - {mes}'
            list_cards[name_col] = {
                'value': round(float(linha['total']), 2),
                'value_max': None,
                'value_min': None,
                'valor_real': None,
                'ano_anterior': None,
                'percentual': round(float(linha['percentual']), 2) if pd.notnull(linha['percentual']) else None,
                'description': f'Mês {linha["data_hora"]}',
                'data_hora': ultima_atualizacao,
                'medida': 'MWh',
            }
        return list_cards
    except Exception as e:
        get_error('get_data_card_energia, ln 295', e)

@desempenho
def get_grafico_nivel(periodo= 'D') -> pd.DataFrame:
    """
    Agrega as colunas de nível por hora ou por dia:
    - periodo == 'M' → média diária
    - periodo == 'D' → média horária
    Retorna um dataframe pronto para plotagem.
    """
    if periodo is None:
        periodo = 'D'
    # --------------------------- prepara dados brutos
    df = st.session_state["dados"].copy()
    # st.write('1 - df: ',df)
    cols_nivel = st.session_state["usina"]["cols_nivel"].split(",")
    cols_nivel = [col for col in cols_nivel if 'nivel' in col]
    # st.write('2 - cols_nivel: ',cols_nivel)

    # garante que 'data_hora' existe e é datetime
    df["data_hora"] = pd.to_datetime(df["data_hora"])
    df = df.set_index("data_hora")

    # --------------------------- escolhe frequência
    freq = {"M": "D", "D": "H"}.get(periodo, "H")  # default → horária

    # --------------------------- resample + média
    df_out = df[cols_nivel].resample(freq).mean().reset_index()

    # opcional: log de depuração
    # st.write(f"Período solicitado: {periodo} → frequência usada: {freq}")
    # st.write("Pré-visualização:", df_out.head())

    return df_out


@desempenho
def get_grafico_energia(periodo, data_inicial, data_final) -> pd.DataFrame:
    try:
        if data_inicial is None:
            data_inicial = datetime.now() - timedelta(days=30)
            data_final = datetime.now()
            periodo = 'D'
        cols_energia = st.session_state['usina']['cols_energia']
        # tabela = st.session_state['usina']['tabela']
        # query = f"SELECT {cols_energia} FROM {tabela} WHERE data_hora BETWEEN '{data_inicial}' AND '{data_final}'"
        get_db_data(data_inicial, data_final)
        cols_energia = cols_energia.split(',')
        # st.write('cols_energia: ',cols_energia)
        df = st.session_state['dados'].copy()
        # st.write('df: ',df)
        df = df[cols_energia]
        data = calcular_energia_acumulada(df, cols_energia, periodo)
        if periodo == 'M':
            # remove a primeira linha
            data = data.iloc[1:]
        return data
    except Exception as e:
        get_error('get_grafico_energia, ln 217', e)

# @desempenho
# def get_ultimos_30_dias(periodo='D', janela=30) -> pd.DataFrame:
#     try:
#         query = get_info_usina('energia total 30 dias')
#         # new_columns = [col for col in st.session_state['usina']['energia'].keys()]
#         cols_energia = st.session_state['usina']['cols_energia'].split(',')
#         df = get_db_data(query)
#         df = df[cols_energia]
#         # df = df.rename(columns=new_columns)
#         data = calcular_energia_acumulada(df, cols_energia, periodo)
#         return data
#     except Exception as e:
#         get_error('get_ultimos_30_dias, ln 190', e)

# @desempenho
# def get_periodo(periodo, data_inicial, data_final) -> pd.DataFrame:
#     try:
#         # energia = ', '.join(st.session_state['usina']['energia'].values())
#         # new_columns = [col for col in st.session_state['usina']['energia'].keys()]
#         cols_energia = st.session_state['usina']['cols_energia']
#         tabela = st.session_state['usina']['tabela']
#         query = f"SELECT {cols_energia} FROM {tabela} WHERE data_hora BETWEEN '{data_inicial}' AND '{data_final}'"
#         df = get_db_data(query)
#         # df = df.rename(columns=new_columns)
#         data = calcular_energia_acumulada(df, cols_energia, periodo)
#         if periodo == 'M':
#             # remove a primeira linha
#             data = data.iloc[1:]
#         return data
#     except Exception as e:
#         get_error('get_periodo, ln 200', e)

# @desempenho
# def get_ultimos_1_hora_nivel(data_hora_inicial, data_hora_final) -> pd.DataFrame:
#     try:
#         # nivel = ', '.join(st.session_state['usina']['nivel'].values())
#         cols_nivel = st.session_state['usina']['cols_nivel'].split(',')
#         nivel = ', '.join(cols_nivel)
#         query = f"SELECT {nivel} FROM {st.session_state['usina']['tabela']} WHERE data_hora BETWEEN '{data_hora_inicial}' AND '{data_hora_final}'"
#         df = get_db_data(query)
#         dif_tempo = (data_hora_final - data_hora_inicial)
#         #  se o tempo for maior que 1 dia, calcular a media movel de 10 minutos diminuindo a quantidade de linhas
#         if dif_tempo.total_seconds() > 86400:
#             df = df.resample('60min', on='data_hora').mean()
#             df = df.reset_index()
#         return df
#     except Exception as e:
#         get_error('get_ultimos_1_hora_nivel, ln 235', e)



@desempenho
def get_names_all_columns() -> pd.DataFrame:
    try:
        query = get_info_usina('nome colunas')
        df = get_db_data(query, verify_type=False)
        return df
    except Exception as e:
        get_error('get_names_all_columns, ln 210', e)

@desempenho
def fetch_dados_graficos(usina, colunas_selecionadas, data_hora_inicial, data_hora_final):
    try:
        query = f"SELECT {', '.join(colunas_selecionadas)} FROM {usina['tabela']} WHERE data_hora BETWEEN '{data_hora_inicial}' AND '{data_hora_final}'"
        df = get_db_data(query)
        return df
    except Exception as e:
        get_error('fetch_dados_graficos, ln 220', e)

@desempenho
def converter_colunas_para_numerico(df, colunas):
    try:
        for col in colunas:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except Exception as e:
        get_error('converter_colunas_para_numerico, ln 215', e)

@desempenho
def get_describe_nivel() -> pd.DataFrame:
    try:
        query = get_info_usina('describe nivel')
        df = get_db_data(query)
        colunas_nivel = [col for col in df.columns if 'niv' in col]
        df = df[colunas_nivel].describe()
        return df
    except Exception as e:
        get_error('get_describe_nivel, ln 224', e)

# @desempenho
# def get_data_inicial(data_inicial=None, data_final=None):
#     colunass = ''
#     table = st.session_state['usina']['tabela']
#     if data_inicial is None:
#         data_inicial = datetime.now() - timedelta(days=240)
#         data_inicial = data_inicial.strftime('%Y-%m-%d %H:%M:%S')
#     if data_final is None:
#         data_final = datetime.now()
#         data_final = data_final.strftime('%Y-%m-%d %H:%M:%S')
#     # print('Colunas: ',colunas)
#     print('colunass: ',colunass)
#     # print('Table: ',table)
#     if isinstance(table, str):
#         for key, value in st.session_state['usina']['energia'].items():
#             colunass += f'{value} as {key}, '
#         for key, value in st.session_state['usina']['nivel'].items():
#             colunass += f'{value} as {key}, '
#         colunass = colunass[:-2]
#         # if query is None:
#         query = f'select {colunass} from {table} where data_hora >= "{data_inicial}" and data_hora <= "{data_final}"'
#         # query = f'select * from {table}"'
#         print('Query: ',query)
#         result = st.session_state['db'].fetch_data(query)   
#         df_ = pd.DataFrame(result)
#         df_ = tratamento_df(df_)
#         # st.session_state['dados'] = df_
#         print('df_.columns: ',df_.columns)
#         print('df_.shape: ',df_.shape)
#     else:
#         df_list = []
#         for key, val in table.items():
#             colunass = ''
#             for col, val in st.session_state['usina']['energia'][key].items():
#                 colunass += f'{val} as {col}, '
#             for col, val in st.session_state['usina']['nivel'][key].items():
#                 colunass += f'{val} as {col}, '
#             colunass = colunass[:-2]
#             query = f'select {colunass} from {table[key]} where data_hora >= "{data_inicial}" and data_hora <= "{data_final}"'
#             print('query: ',query)
            
#             result = st.session_state['db'].fetch_data(query)   
#             df_a = pd.DataFrame(result)
#             df_aux = tratamento_df(df_a)
#             df_aux['data_hora'] = df_aux['data_hora'].dt.round('min')
#             print('Tabela: ',table[key])
#             print('df_aux.columns: ',df_aux.columns)
#             print('df_aux.shape: ',df_aux.shape)
#             print('1 values: ',df_aux.values[0])
#             print('2 values: ',df_aux.values[-1])
#             print('--------------------------------')
#             df_list.append(df_aux)
#         # df_ = pd.concat(df_list)
#         # df_merged = pd.merge(df_list[0], df_list[1], on='data_hora', how='outer')
#         df_ = pd.merge(df_list[0], df_list[1], on='data_hora', how='outer')
#         print('df_.columns: ',df_.columns)
#         print('df_.shape: ',df_.shape)
#     st.session_state['dados'] = df_
#     # print('2. st.session_state: ',st.session_state['dados'].shape)

# @desempenho
# def get_db_data(query: str, verify_type: bool = True) -> pd.DataFrame:
#     try:        
#         if st.session_state['dados'].empty:
#             st.warning('Tivemos um erro na consulta do banco de dados. Atualize essa pagina para tentar novamente e tente outro periodo de tempo.')
#             return
#         # # Utiliza a função utilitária para extrair informações
#         info_query = parse_query_info(query)

#         # intervalo máximo desejado
#         JANELA = pd.Timedelta(minutes=10)

#         # datas pedidas pelo usuário
#         data_inicial = pd.to_datetime(info_query["data_inicial"])
#         data_final   = pd.to_datetime(info_query["data_final"]) - JANELA

#         # datas existentes na base
#         data_inicial_st = st.session_state["dados"]["data_hora"].min()
#         data_final_st   = st.session_state["dados"]["data_hora"].max()

#         # checa se o intervalo pedido está fora dos seus dados
#         inicio_antes_do_que_tenho = data_inicial < data_inicial_st
#         fim_depois_do_que_tenho   = data_final   > data_final_st

#         st.write(
#             "data_inicial: ", data_inicial,
#             "data_inicial_st: ", data_inicial_st,
#             "→ data_inicial < data_inicial_st ?", inicio_antes_do_que_tenho
#         )
#         st.write(
#             "data_final: ", data_final,
#             "data_final_st: ", data_final_st,
#             "→ data_final > data_final_st ?",   fim_depois_do_que_tenho
#         )

#         # Se quiser saber se o intervalo está COMPLETAMENTE dentro da faixa de dados:
#         intervalo_ok = (data_inicial >= data_inicial_st) & (data_final <= data_final_st)
#         st.write("Intervalo pedido está dentro da faixa de dados? ", intervalo_ok)
#         # colunas = info_query['colunas']
#         # data_inicial = pd.to_datetime(info_query['data_inicial'])
#         # data_final = pd.to_datetime(info_query['data_final'])
#         # data_inicial_st = pd.to_datetime(st.session_state['dados']['data_hora'].min())
#         # data_final_st = pd.to_datetime(st.session_state['dados']['data_hora'].max())
#         st.write('data_inicial: ',data_inicial, 'data_incial_st: ',data_inicial_st,' result: ',data_inicial > data_final_st)
#         st.write('data_final: ',data_final, 'data_final_st: ',data_final_st,' result: ',data_final < data_inicial_st)
#         if not intervalo_ok:
#             print(1,f'logica 1: {data_inicial} > {data_final_st} or {data_final} < {data_inicial_st}')
#             get_data_inicial(data_inicial, data_final, query=None)
#             df_ = st.session_state['dados']
#             st.write('Não está no intervalo: df_: ',df_)
#         else:
#             print(2,f'logica 2: {data_inicial}, {data_final_st} and {data_final}, {data_inicial_st}')
#             df_ = st.session_state['dados'].copy()
#             df_ = df_[(df_['data_hora'] >= data_inicial) & (df_['data_hora'] <= data_final)]
#             st.write('Está no intervalo: df_: ',df_)
#             # df_ = df_[colunas]
#             # df_ = rename_colunas(df_)

#         # print('3. df_: ',df_.shape, 'Colunas: ',df_.columns)
#         print('df_.columns: ',df_.columns)
#         print('df_.shape: ',df_.shape)
#         return df_ 
#     except Exception as e:
#         # print(e)
#         get_error('get_db_data', e)