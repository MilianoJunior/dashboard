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
        # excluir valores iguais a 103.00
        mask = (df[colunas_energia] == 103.00).any(axis=1)
        df = df[~mask]
        df_diario = df.groupby(df['data_hora'].dt.date).last()
        
        # Converter para float (vetorizado)
        df_diario[colunas_energia] = df_diario[colunas_energia].apply(pd.to_numeric, errors='coerce').astype(float)
        
        # Otimização: usar .diff() ao invés de loop - MUITO mais rápido
        for col in colunas_energia:
            df_diario[f'prod_{col}'] = df_diario[col].diff()
        
        # eliminar as linhas que tem None
        df_diario = df_diario.fillna(0)
        df_diario = df_diario.drop(columns=['data_hora'], errors='ignore')
        df_diario = df_diario.drop(columns=colunas_energia)
        
        return df_diario
    if periodo == 'M':
        colunas_energia = [col for col in colunas if 'energia' in col]

        mask = (df[colunas_energia] == 103.00).any(axis=1)
        df = df[~mask]
        
        # Criar chave ano-mês para agrupar corretamente pelos meses
        df['ano_mes'] = df['data_hora'].dt.strftime('%Y-%m')
        df_mensal = df.groupby('ano_mes').last()
        
        # Converter para float (vetorizado)
        df_mensal[colunas_energia] = df_mensal[colunas_energia].apply(pd.to_numeric, errors='coerce').astype(float)
        
        # Calcular a diferença para cada coluna de energia
        if len(df_mensal) < 6:
            # registrar o mês anterior com o valor 0
            last_month = df_mensal.index[0]
            after_last_month = datetime.strptime(last_month, '%Y-%m') - timedelta(days=30)
            after_last_month = after_last_month.strftime('%Y-%m')
            for col in colunas_energia:
                df_mensal.loc[after_last_month, col] = 0
            df_mensal = df_mensal.sort_index()
        
        # Otimização: usar .diff() ao invés de loop - MUITO mais rápido
        for col in colunas_energia:
            df_mensal[f'prod_{col}'] = df_mensal[col].diff()
        
        # substituir os valores None por 0
        df_mensal = df_mensal.fillna(0)
        df_mensal = df_mensal.drop(columns=colunas_energia)
        
        colunas_mensal = list(df_mensal.columns)
        print('colunas_mensal: ',colunas_mensal)
        if 'data_hora' in colunas_mensal:
            print('data_hora encontrado')
            df_mensal = df_mensal.drop(columns=['data_hora'])
        
        return df_mensal
    if periodo == 'H':
        colunas_energia = [col for col in colunas if 'energia' in col]
        mask = (df[colunas_energia] == 103.00).any(axis=1)
        df = df[~mask]
        df['hora'] = df['data_hora'].dt.floor('h')  # lowercase 'h' para evitar warning
        df_hora = df.groupby('hora').last().reset_index()
        
        # Converter para float (vetorizado)
        df_hora[colunas_energia] = df_hora[colunas_energia].apply(pd.to_numeric, errors='coerce').astype(float)

        # Otimização: usar .diff() ao invés de loop - MUITO mais rápido
        for col in colunas_energia:
            df_hora[f'prod_{col}'] = df_hora[col].diff()

        df_hora = df_hora.fillna(0)
        df_hora = df_hora.drop(columns=colunas_energia)
        df_hora = df_hora.drop(columns=['data_hora'], errors='ignore')
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

