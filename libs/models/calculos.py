from libs.utils.decorators import desempenho, get_error
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
# from libs.models.datas import get_db_data, get_info_usina

@desempenho
def retira_outliers(df, colunas):
    for col in colunas:
        if col == 'data_hora':
            continue
        print(f'Coluna: {col}')
        print(df[col].describe())
        df[col] = df[col].clip(lower=df[col].quantile(0.01), upper=df[col].quantile(0.99))
    return df

@desempenho
def calcular_energia_acumulada(df, colunas, periodo):
    print(f'Periodo: {periodo}')
    print('df.shape: ',df.shape)
    print('colunas: ',colunas)
    print('--'*10)
    
    if periodo == 'D':
        # Agrupa por dia e pega o último valor de cada dia para cada coluna
        colunas_energia = [col for col in colunas if 'energia' in col]
        # df['data_hora'] = df['data_hora'].dt.date
        # excluir valores iguais a 103.00
        mask = (df[colunas_energia] == 103.00).any(axis=1)
        df = df[~mask]
        df_diario = df.groupby(df['data_hora'].dt.date).last()
        # Converter para float
        for col in colunas_energia:
            if col in df_diario.columns:
                df_diario[col] = pd.to_numeric(df_diario[col], errors='coerce').astype(float)
        # Calcular a diferença para cada coluna de energia
        for col in colunas_energia:
            for i in range(1, len(df_diario)):
                df_diario.loc[df_diario.index[i], f'prod_{col}'] = df_diario[col].values[i] - df_diario[col].values[i-1]

        
        # eliminar as linhas que tem None
        # df_diario = df_diario.dropna(axis=0)
        df_diario = df_diario.fillna(0)
        df_diario = df_diario.drop(columns=['data_hora'])
        df_diario = df_diario.drop(columns=colunas_energia)
        
        return df_diario
    if periodo == 'M':
        
        colunas_energia = [col for col in colunas if 'energia' in col]

        mask = (df[colunas_energia] == 103.00).any(axis=1)
        df = df[~mask]
        # Criar chave ano-mês para agrupar corretamente pelos meses
        df['ano_mes'] = df['data_hora'].dt.strftime('%Y-%m')
        # Agrupar pela chave ano-mês e pegar o último registro de cada mês
        df_mensal = df.groupby('ano_mes').last()
        # Converter para float
        for col in colunas_energia:
            if col in df_mensal.columns:
                df_mensal[col] = pd.to_numeric(df_mensal[col], errors='coerce').astype(float)
        # Calcular a diferença para cada coluna de energia
        if len(df_mensal) < 6:
            # registrar o mês anterior com o valor 0
            last_month = df_mensal.index[0]
            after_last_month = datetime.strptime(last_month, '%Y-%m') - timedelta(days=30)
            after_last_month = after_last_month.strftime('%Y-%m')
            for col in colunas_energia:
                df_mensal.loc[after_last_month, col] = 0
            df_mensal = df_mensal.sort_index()
        for col in colunas_energia:
            for i in range(1, len(df_mensal)):
                df_mensal.loc[df_mensal.index[i], f'prod_{col}'] = df_mensal[col].values[i] - df_mensal[col].values[i-1]
        # eliminar as linhas que tem None
        # st.write('df_mensal: ',df_mensal)
        # df_mensal = df_mensal.dropna(axis=0)
        
        # df_mensal = df_mensal.drop(columns=['data_hora'])
        # substituir os valores None por 0
        df_mensal = df_mensal.fillna(0)
        df_mensal = df_mensal.drop(columns=colunas_energia)
        colunas_mensal = list(df_mensal.columns)
        print('colunas_mensal: ',colunas_mensal)
        if 'data_hora' in colunas_mensal:
            print('data_hora encontrado')
            df_mensal = df_mensal.drop(columns=['data_hora'])
        # df_mensal.set_index('ano_mes', inplace=True)
        # st.write('2 - df_mensal: ',df_mensal)
        return df_mensal
    if periodo == 'H':
        colunas_energia = [col for col in colunas if 'energia' in col]
        mask = (df[colunas_energia] == 103.00).any(axis=1)
        df = df[~mask]
        df['hora'] = df['data_hora'].dt.floor('H')  # ou .dt.round('H') se preferir arredondar
        df_hora = df.groupby('hora').last().reset_index()
        for col in colunas_energia:
            if col in df_hora.columns:
                df_hora[col] = pd.to_numeric(df_hora[col], errors='coerce').astype(float)

        for col in colunas_energia:
            for i in range(1, len(df_hora)):
                df_hora.loc[df_hora.index[i], f'prod_{col}'] = df_hora[col].values[i] - df_hora[col].values[i-1]

        df_hora = df_hora.fillna(0)
        df_hora = df_hora.drop(columns=colunas_energia)
        df_hora = df_hora.drop(columns=['data_hora'])
        df_hora.set_index('hora', inplace=True)
        return df_hora
    return df


@desempenho
def get_total_gerado() -> pd.DataFrame:
    try:
        # colunas_energia = list(st.session_state['usina']['energia'].values())
        # query_energia = get_info_usina('energia total')
        # data = get_db_data(query_energia)
        # if data.empty:
        #     return pd.DataFrame(columns=['total'])
        # data['total'] = data[[col for col in colunas_energia if 'energia' in col]].sum(axis=1)
        return pd.DataFrame(columns=['total'])
    except Exception as e:
        get_error('get_total_gerado, ln 160', e)