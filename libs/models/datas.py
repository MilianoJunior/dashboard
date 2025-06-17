from libs.utils.decorators import desempenho, get_error
from libs.models.db import Database
from libs.models.calculos import calcular_energia_acumulada
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import numpy as np
from libs.utils.db_utils import init_db_connection

@desempenho
def get_db_data(query: str, verify_type: bool = True) -> pd.DataFrame:
    try:
        # Garante que a conexão está inicializada
        if 'db' not in st.session_state or st.session_state['db'] is None:
            init_db_connection()
        if st.session_state['db'] is None:
            raise Exception('Conexão com o banco de dados não inicializada.')
        result = st.session_state['db'].fetch_data(query)
        # salvar todos os dados em um arquivo csv
        df_ = st.session_state['db'].fetch_data('select * from cgh_picadas_altas')
        df1 = pd.DataFrame(df_)
        # df1.to_csv('cgh_picadas_altas.csv', index=False)
        # print('salvo')
        # print('#####'*20)
        df_ = pd.DataFrame(result)
        if not verify_type:
            return df_
        for col in df_.dtypes.index:
            if df_[col].dtype != 'int64' and df_[col].dtype != 'float64' and col != 'data_hora':
                if pd.to_numeric(df_[col], errors='coerce').notna().all():
                    df_[col] = df_[col].astype(float)
                    df_[col] = df_[col].fillna(0)
        colunas_numericas = df_.select_dtypes(include=[np.number]).columns
        mask = (df_[colunas_numericas] >= 0).all(axis=1)
        df_ = df_[mask]
        if df_.empty:
            return df_
        return df_
    except Exception as e:
        # print(e)
        get_error('get_db_data', e)

@desempenho
def get_info_usina(comando: str) -> str:
    try:
        energia = ', '.join(st.session_state['usina']['energia'].values())
        nivel = ', '.join(st.session_state['usina']['nivel'].values())
        data_inicial = datetime.now() - timedelta(days=30)
        data_inicial_180 = datetime.now() - timedelta(days=180)
        data_final = datetime.now()
        data_inicial_nivel = datetime.now() - timedelta(hours=1)
        data_final_nivel = datetime.now()
        # f"SELECT {', '.join(colunas_selecionadas)} FROM {usina['tabela']} WHERE data_hora BETWEEN '{data_hora_inicial}' AND '{data_hora_final}'"
        comandos = {
            'energia total': f"SELECT {energia} FROM {st.session_state['usina']['tabela']} ORDER BY data_hora DESC LIMIT 1",
            'energia total 30 dias': f"SELECT {energia} FROM {st.session_state['usina']['tabela']} WHERE data_hora BETWEEN '{data_inicial}' AND '{data_final}'",
            'energia total 180 dias': f"SELECT {energia} FROM {st.session_state['usina']['tabela']} WHERE data_hora BETWEEN '{data_inicial_180}' AND '{data_final}'",
            'describe nivel': f"SELECT {nivel} FROM {st.session_state['usina']['tabela']} ORDER BY data_hora DESC LIMIT 60",
            'nivel': f"SELECT {nivel} FROM {st.session_state['usina']['tabela']} WHERE data_hora BETWEEN '{data_inicial_nivel}' AND '{data_final_nivel}'",
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
        query = get_info_usina('energia total 180 dias')
        df = get_db_data(query)
        data = calcular_energia_acumulada(df, list(st.session_state['usina']['energia'].values()), 'M')
        cols_energia = list(st.session_state['usina']['energia'].values())
        # data[cols_energia] = data[cols_energia].apply(pd.to_numeric, errors='coerce').clip(lower=0)
        # if not pd.api.types.is_datetime64_any_dtype(data['data_hora']):
        #     data['data_hora'] = pd.to_datetime(data['data_hora'], errors='coerce')
        meses_pt = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        data['data_hora'] = data['data_hora'].dt.month.apply(lambda x: meses_pt[x-1])
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
        valores_fae = {
            'Janeiro/2025': 4.95,
            'Janeiro/2024': 208.65,
            'Fevereiro/2024': None,
            'Março/2024': None,
            'Abril/2024': 2.879,
            'Maio/2024': 3.052,
            'Junho/2024': 1.111,
            'Julho/2024': 0.764,
            'Agosto/2024': 0.524,
            'Setembro/2024': 1.954,
            'Outubro/2024': 4.764,
            'Novembro/2024': None,
            'Dezembro/2024': None,
            'Fevereiro/2025': None,
        }
        for index, linha in ultimos_180_dias.iterrows():
            mes = f'{linha['data_hora']}'
            name_col = f'Geração - {mes}/2025'
            mes_anterior = f'{mes}/2024'
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
def get_temperatura() -> pd.DataFrame:
    try:
        query = get_info_usina('describe temperatura')
        df = get_db_data(query)
        colunas_temp = [col for col in df.columns if 'temp' in col or 'enrol' in col]
        df = df[colunas_temp]
        df = df.describe()
        return df
    except Exception as e:
        get_error('get_temperatura, ln 301', e)

@desempenho
def get_ultimos_30_dias(periodo='D', janela=30) -> pd.DataFrame:
    try:
        query = get_info_usina('energia total 30 dias')
        df = get_db_data(query)
        data = calcular_energia_acumulada(df, list(st.session_state['usina']['energia'].values()), periodo)
        return data
    except Exception as e:
        get_error('get_ultimos_30_dias, ln 190', e)

def get_periodo(periodo, data_inicial, data_final) -> pd.DataFrame:
    try:
        energia = ', '.join(st.session_state['usina']['energia'].values())
        tabela = st.session_state['usina']['tabela']
        query = f"SELECT {energia} FROM {tabela} WHERE data_hora BETWEEN '{data_inicial}' AND '{data_final}'"
        df = get_db_data(query)
        data = calcular_energia_acumulada(df, list(st.session_state['usina']['energia'].values()), periodo)
        if periodo == 'M':
            # remove a primeira linha
            data = data.iloc[1:]
        return data
    except Exception as e:
        get_error('get_periodo, ln 200', e)

@desempenho
def get_ultimos_1_hora_nivel(data_hora_inicial, data_hora_final) -> pd.DataFrame:
    try:
        nivel = ', '.join(st.session_state['usina']['nivel'].values())
        query = f"SELECT {nivel} FROM {st.session_state['usina']['tabela']} WHERE data_hora BETWEEN '{data_hora_inicial}' AND '{data_hora_final}'"
        df = get_db_data(query)
        dif_tempo = (data_hora_final - data_hora_inicial)
        #  se o tempo for maior que 1 dia, calcular a media movel de 10 minutos diminuindo a quantidade de linhas
        if dif_tempo.total_seconds() > 86400:
            df = df.resample('60min', on='data_hora').mean()
            df = df.reset_index()
        return df
    except Exception as e:
        get_error('get_ultimos_1_hora_nivel, ln 235', e)

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