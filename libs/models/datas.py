from libs.utils.decorators import desempenho, get_error, get_error_cached
from libs.models.db import Database
from libs.models.calculos import calcular_energia_acumulada
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import numpy as np
from libs.utils.db_utils import init_db_connection
import re
from functools import lru_cache

@desempenho
def convert_padronizado_to_real(cols_padronizadas: str, mapeamento: dict, is_multi_table: bool = False) -> str:
    """
    Converte nomes de colunas padronizadas para nomes reais do banco.
    
    Args:
        cols_padronizadas: String com colunas padronizadas separadas por vírgula (ex: "data_hora,energia_ug01")
        mapeamento: Dict com mapeamento {nome_padronizado: nome_real}
        is_multi_table: Se True, usa apenas ug01 do mapeamento multi-tabela
    
    Returns:
        String com nomes reais das colunas (ex: "data_hora,acumulador_energia")
    """
    cols_list = [col.strip() for col in cols_padronizadas.split(',')]
    cols_reais = []
    
    # Se é multi-tabela (Pedras, Hoppen), pegar apenas ug01
    if is_multi_table and isinstance(mapeamento, dict) and 'ug01' in mapeamento:
        mapeamento = mapeamento['ug01']
    
    for col_padrao in cols_list:
        # Se está no mapeamento, pegar o nome real; senão, usar o próprio nome (ex: data_hora)
        col_real = mapeamento.get(col_padrao, col_padrao)
        cols_reais.append(col_real)
    
    return ','.join(cols_reais)

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
                # df_[col] = df_[col].fillna(0)
        colunas_numericas = df_.select_dtypes(include=[np.number]).columns
        mask = (df_[colunas_numericas] >= 10).all(axis=1)
    
        df_ = df_[mask]
    return df_

# def tratamento_aparecida(df_):
#     cont = 0
#     chave = False
#     for index in range(len(df_)):
#         if df_['data_hora'].iloc[index] >= datetime(2025, 10, 14, 3, 35, 0):
#             soma = float(df_['energia_ug01'].iloc[index]) - float(df_['energia_ug01'].iloc[index-1])
#             if not chave:
#                 cont += 1
#             if soma < 0 or chave:
#                 chave = True
#                 print(cont , ' index: ',index, 'data_hora: ',df_['data_hora'].iloc[index], 'energia_ug01: ',df_['energia_ug01'].iloc[index], '-', df_['energia_ug01'].iloc[index-1])
#                 df_['energia_ug01'].iloc[index] = df_['energia_ug01'].iloc[index] + 9971.39
#     return df_


def tratamento_aparecida(df_, *, 
                         col_time='data_hora', 
                         col_energy='energia_ug01',
                         threshold=pd.Timestamp(2025, 10, 14, 3, 35, 0),
                         offset=9971.39):
    df = df_.copy()

    # garante tipos
    df[col_time] = pd.to_datetime(df[col_time], errors='coerce')
    s_mask = df[col_time] >= threshold

    # se não há nada na janela, apenas retorna
    if not s_mask.any():
        return df, 0, None

    # vetor dentro da janela
    idx_win = df.index[s_mask]
    s = pd.to_numeric(df.loc[idx_win, col_energy], errors='coerce').to_numpy()

    # diffs sucessivas dentro da janela
    d = np.diff(s)

    # encontra a primeira posição onde houve queda (diff < 0)
    neg_pos = np.where(d < 0)[0]
    if neg_pos.size == 0:
        # não houve queda; cont = total na janela; nada é ajustado
        return df, len(idx_win), None

    first_rel = int(neg_pos[0]) + 1           # +1 porque diff é deslocado
    first_idx = idx_win[first_rel]            # índice absoluto no df
    cont = first_rel                          # mesmo significado do seu cont

    # aplica o offset da primeira queda em diante (incluindo a linha da queda)
    df.loc[first_idx:, col_energy] = pd.to_numeric(df.loc[first_idx:, col_energy], errors='coerce') + offset

    # info opcional da "quebra" para depuração
    info_quebra = {
        'index': int(first_idx),
        'data_hora': df.at[first_idx, col_time],
        'energia_antes': float(s[first_rel]),
        'energia_antes_prev': float(s[first_rel-1]),
        'diff': float(s[first_rel] - s[first_rel-1]),
        'offset_aplicado': float(offset)
    }

    return df, cont, info_quebra

@desempenho
def get_db_data(data_inicial, data_final):
    print('  14 - função principal: get_db_data')
    table = st.session_state['usina']['tabela']
    # Otimização: reduzir janela de 240 para 180 dias (conforme nome da função sugere)
    data_inicial = data_inicial or (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d %H:%M:%S')
    data_final = data_final or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data_inicial = pd.to_datetime(data_inicial)
    data_final = pd.to_datetime(data_final)
    print('data_inicial: ', data_inicial, type(data_inicial))
    print('data_final: ', data_final, type(data_final))
    
    def build_columns(energia, nivel):
        return ', '.join(f'{v} as {k}' for d in [energia, nivel] for k, v in d.items())
    
    def fetch_and_process(table_name, energia, nivel, is_multi=False):
        # Otimização: buscar apenas energia se não precisar de nível imediatamente
        # Para dados gerais, incluir tudo. Para específicos, otimizar.
        colunass = build_columns(energia, nivel)
        query = f'SELECT {colunass} FROM {table_name} WHERE data_hora >= "{data_inicial}" AND data_hora <= "{data_final}"'
        if 'contador' in st.session_state:
            st.session_state.contador += 1
        print(' ')
        print('query: ', query, 'contador: ', st.session_state.contador)
        print(' ')
        result = st.session_state['db'].fetch_data(query)            
        df = pd.DataFrame(result)
        df = tratamento_df(df)

        if is_multi:
            df['data_hora'] = df['data_hora'].dt.round('min')
        # df = tratamento_aparecida(df)
        # st.write(table_name, ' 1 - função principal: get_db_data, df: ', df, 'contador: ', st.session_state.contador,'state: ', st.session_state.ultima_atualizacao)
        return df
    
    if isinstance(table, str):
        print('    1- Sem merge')
        energia = st.session_state['usina']['energia']
        nivel = st.session_state['usina']['nivel']
        df_ = fetch_and_process(table, energia, nivel)
        # if st.session_state.get('dados_geral') is None:
        #     print('    1- Sem dados')
        #     df_ = fetch_and_process(table, energia, nivel)
        if 'aparecida' in table:
            df_, cont, info = tratamento_aparecida(df_)
            
        # else:
        #     print('    2- Com dados')
        #     df_ = st.session_state['dados']
        #     if df_ is None or df_.empty:
        #         print('    3- Sem dados')
        #         df_ = fetch_and_process(table, energia, nivel)
        #     if df_['data_hora'].iloc[-1] < data_inicial and df_['data_hora'].iloc[0] > data_final:
        #         print('    3- Sem dados no intervalo')
        #         df_ = fetch_and_process(table, energia, nivel)
        #     else:
        #         print('    4- Com dados no intervalo')
        #         df_ = st.session_state['dados_geral']
        #         # st.write('df_: ', df_)
        #         # filtrar e enviar apenas os dados no intervalo de data_inicial e data_final
        #         df_ = df_[(df_['data_hora']>=data_inicial) & (df_['data_hora']<=data_final)]
        #         st.write('df_filtrado: ', df_)
    else:
        print('    2- Com merge')
        df_list = [fetch_and_process(table[key], st.session_state['usina']['energia'][key],
                                     st.session_state['usina']['nivel'][key], is_multi=True)
                   for key in table]
        print('  16 - função principal: get_db_data, df_list: ')
        df_ = pd.merge(df_list[0], df_list[1], on='data_hora', how='outer')
    
    st.session_state['dados_geral'] = df_
    st.session_state['dados'] = st.session_state['dados_geral'].copy()
    

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
        
        # Determinar qual tabela usar
        if isinstance(st.session_state['usina']['tabela'], dict):
            # Se tabela é um dicionário, usar a primeira tabela
            tabela_nome = list(st.session_state['usina']['tabela'].values())[0]
        else:
            # Se tabela é uma string, usar diretamente
            tabela_nome = st.session_state['usina']['tabela']
        
        # f"SELECT {', '.join(colunas_selecionadas)} FROM {usina['tabela']} WHERE data_hora BETWEEN '{data_hora_inicial}' AND '{data_hora_final}'"
        comandos = {
            'energia total': f"SELECT {cols_energia} FROM {tabela_nome} ORDER BY data_hora DESC LIMIT 1",
            'energia total 30 dias': f"SELECT {cols_energia} FROM {tabela_nome} WHERE data_hora BETWEEN '{data_inicial}' AND '{data_final}'",
            'energia total 180 dias': f"SELECT {cols_energia} FROM {tabela_nome} WHERE data_hora BETWEEN '{data_inicial_180}' AND '{data_final}'",
            'describe nivel': f"SELECT {cols_nivel} FROM {tabela_nome} ORDER BY data_hora DESC LIMIT 60",
            'nivel': f"SELECT {cols_nivel} FROM {tabela_nome} WHERE data_hora BETWEEN '{data_inicial_nivel}' AND '{data_final_nivel}'",
            'nome colunas': f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{tabela_nome}'",
            'describe temperatura': f"SELECT * FROM {tabela_nome} ORDER BY data_hora DESC LIMIT 120",
        }
        if comando not in comandos:
            raise ValueError(f"Comando '{comando}' não encontrado")
        return comandos[comando]
    except Exception as e:
        get_error('get_info_usina, ln 155', e)

@st.cache_data(ttl=21600, show_spinner="Carregando dados mensais...")  # Cache de 6 horas
def _get_dados_mensais_cached(tabela: str, cols_energia_padrao: str, cols_energia_real: str, data_inicial_str: str, data_final_str: str, usina_nome: str):
    """
    Função auxiliar com cache para buscar e processar dados mensais.
    Usa apenas tipos hashable para funcionar com st.cache_data.
    
    Args:
        cols_energia_padrao: Nomes padronizados para processar dados (ex: "data_hora,energia_ug01")
        cols_energia_real: Nomes reais das colunas no banco (ex: "data_hora,acumulador_energia")
    """
    # Construir query com nomes REAIS do banco
    query = f'SELECT {cols_energia_real} FROM {tabela} WHERE data_hora >= "{data_inicial_str}" AND data_hora <= "{data_final_str}"'
    
    # Buscar dados
    result = st.session_state['db'].fetch_data(query)
    df = pd.DataFrame(result)
    
    # IMPORTANTE: Renomear colunas para nomes padronizados para o resto do código funcionar
    cols_real_list = [c.strip() for c in cols_energia_real.split(',')]
    cols_padrao_list = [c.strip() for c in cols_energia_padrao.split(',')]
    rename_map = dict(zip(cols_real_list, cols_padrao_list))
    df = df.rename(columns=rename_map)
    df = tratamento_df(df)
    
    # Tratamento especial para aparecida
    if 'aparecida' in tabela:
        df, cont, info = tratamento_aparecida(df)
    
    # Processar para mensal - usar nomes padronizados
    cols_list = cols_energia_padrao.split(',')
    df = df[cols_list]
    data = calcular_energia_acumulada(df, cols_list, 'M')
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
    
    return data

@desempenho
def get_ultimos_180_dias_mensal() -> pd.DataFrame:
    try:
        print('  13 - função principal: get_ultimos_180_dias_mensal (com cache)')
        
        # Preparar parâmetros hashable para cache
        tabela = st.session_state['usina']['tabela']
        is_multi_table = isinstance(tabela, dict)  # True para Pedras/Hoppen
        
        if is_multi_table:
            tabela = list(tabela.values())[0]  # Pegar primeira tabela (ug01)
            # Para multi-tabela, buscar apenas colunas da UG01
            cols_energia_padrao = 'data_hora,energia_ug01'  # ✅ Apenas UG01!
        else:
            cols_energia_padrao = st.session_state['usina']['cols_energia']
        
        usina_nome = st.session_state['usina'].get('users', 'default')
        
        # Converter nomes padronizados para nomes reais do banco
        mapeamento_energia = st.session_state['usina']['energia']
        cols_energia_real = convert_padronizado_to_real(cols_energia_padrao, mapeamento_energia, is_multi_table)
        
        data_inicial = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d %H:%M:%S')
        data_final = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Logs removidos para produção - performance otimizada
        
        # Usar função com cache
        data = _get_dados_mensais_cached(tabela, cols_energia_padrao, cols_energia_real, data_inicial, data_final, usina_nome)
        
        # Extrair ultima_atualizacao dos dados cached (não precisa query extra!)
        if not data.empty and 'data_hora' in data.columns:
            # Pegar a última data do DataFrame mensal
            ultima_data = data['data_hora'].iloc[-1] if len(data) > 0 else None
            if ultima_data:
                st.session_state['ultima_atualizacao'] = ultima_data
        
        # Só atualizar session state se realmente necessário (para outras funções que usam)
        if 'dados' not in st.session_state or st.session_state.get('dados') is None:
            # Buscar apenas dados recentes (últimos 30 dias) ao invés de 180 dias!
            data_inicial_recente = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
            data_final_recente = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            get_db_data(data_inicial=data_inicial_recente, data_final=data_final_recente)
        
        return data
    except Exception as e:
        get_error('get_ultimos_180_dias_mensal, ln 205', e)
        return pd.DataFrame()


@desempenho
def get_data_card_energia() -> dict:
    try:
        print('  11 - função principal: get_data_card_energia')
        ultimos_180_dias = get_ultimos_180_dias_mensal()
        print('  12 - filtros')
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

@st.cache_data(ttl=300, show_spinner="Carregando gráfico de nível...")  # Cache de 5 minutos
def _get_grafico_nivel_cached(tabela: str, cols_nivel_padrao: str, cols_nivel_real: str, data_inicial_str: str, data_final_str: str, periodo: str, usina_nome: str):
    """
    Função auxiliar com cache para gráfico de nível.
    """
    # Query otimizada - buscar apenas últimas N horas para nível (não precisa de 180 dias)
    if periodo == 'D':
        dias_buscar = 30
    else:
        dias_buscar = 7
    
    data_inicio_nivel = (datetime.now() - timedelta(days=dias_buscar)).strftime('%Y-%m-%d %H:%M:%S')
    
    # Buscar apenas colunas de nível com nomes REAIS
    query = f'SELECT data_hora, {cols_nivel_real} FROM {tabela} WHERE data_hora >= "{data_inicio_nivel}" AND data_hora <= "{data_final_str}"'
    
    result = st.session_state['db'].fetch_data(query)
    df = pd.DataFrame(result)
    
    # Renomear colunas para nomes padronizados
    cols_real_list = ['data_hora'] + [c.strip() for c in cols_nivel_real.split(',') if c.strip() != 'data_hora']
    cols_padrao_list = ['data_hora'] + [c.strip() for c in cols_nivel_padrao.split(',') if c.strip() != 'data_hora']
    rename_map = dict(zip(cols_real_list, cols_padrao_list))
    df = df.rename(columns=rename_map)
    
    df = tratamento_df(df)
    
    cols_list = [col for col in cols_nivel_padrao.split(',') if 'nivel' in col]
    
    # garante que 'data_hora' existe e é datetime
    df["data_hora"] = pd.to_datetime(df["data_hora"])
    df = df.set_index("data_hora")

    # escolhe frequência
    freq = {"M": "D", "D": "h"}.get(periodo, "h")  # lowercase 'h' para evitar warning

    # resample + média
    df_out = df[cols_list].resample(freq).mean().reset_index()

    # forward fill para valores None
    df_out = df_out.ffill()

    return df_out

@desempenho
def get_grafico_nivel(periodo= 'D') -> pd.DataFrame:
    """
    Agrega as colunas de nível por hora ou por dia:
    - periodo == 'M' → média diária
    - periodo == 'D' → média horária
    Retorna um dataframe pronto para plotagem.
    """
    try:
        if periodo is None:
            periodo = 'D'
        
        # Preparar parâmetros para cache
        tabela = st.session_state['usina']['tabela']
        is_multi_table = isinstance(tabela, dict)
        
        if is_multi_table:
            tabela = list(tabela.values())[0]
            # Para multi-tabela, pegar apenas colunas que existem na UG01
            # Do YAML: nivel.ug01 = {'nivel_montante': '...', 'nivel_jusante_ug01': '...'}
            # Então usar apenas essas colunas padronizadas
            cols_nivel_padrao = 'data_hora,nivel_montante,nivel_jusante_ug01'  # Colunas da UG01
        else:
            cols_nivel_padrao = st.session_state["usina"]["cols_nivel"]
        
        usina_nome = st.session_state['usina'].get('users', 'default')
        
        # Converter nomes padronizados para nomes reais
        mapeamento_nivel = st.session_state['usina']['nivel']
        
        # Pegar apenas as colunas de nível (sem data_hora)
        cols_nivel_so_nivel = ','.join([c.strip() for c in cols_nivel_padrao.split(',') if 'nivel' in c])
        cols_nivel_real = convert_padronizado_to_real(cols_nivel_so_nivel, mapeamento_nivel, is_multi_table)
        
        data_inicial_str = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        data_final_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Usar cache
        return _get_grafico_nivel_cached(tabela, cols_nivel_padrao, cols_nivel_real, data_inicial_str, data_final_str, periodo, usina_nome)
    except Exception as e:
        get_error('get_grafico_nivel', e)
        return pd.DataFrame()

@st.cache_data(ttl=300, show_spinner="Carregando gráfico de energia...")  # Cache de 5 minutos
def _get_grafico_energia_cached(tabela: str, cols_energia_padrao: str, cols_energia_real: str, data_inicial_str: str, data_final_str: str, periodo: str, usina_nome: str):
    """
    Função auxiliar com cache para gráfico de energia.
    """
    # Query otimizada - buscar apenas colunas de energia com nomes REAIS
    query = f'SELECT {cols_energia_real} FROM {tabela} WHERE data_hora >= "{data_inicial_str}" AND data_hora <= "{data_final_str}"'
    
    result = st.session_state['db'].fetch_data(query)
    df = pd.DataFrame(result)
    
    # Renomear colunas para nomes padronizados
    cols_real_list = [c.strip() for c in cols_energia_real.split(',')]
    cols_padrao_list = [c.strip() for c in cols_energia_padrao.split(',')]
    rename_map = dict(zip(cols_real_list, cols_padrao_list))
    df = df.rename(columns=rename_map)
    
    df = tratamento_df(df)
    
    # Tratamento especial para aparecida
    if 'aparecida' in tabela:
        df, cont, info = tratamento_aparecida(df)
    
    cols_list = cols_energia_padrao.split(',')
    df = df[cols_list]
    data = calcular_energia_acumulada(df, cols_list, periodo)
    if periodo == 'M':
        data = data.iloc[1:]
    return data

@desempenho
def get_grafico_energia(periodo, data_inicial, data_final) -> pd.DataFrame:
    try:
        if data_inicial is None:
            data_inicial = datetime.now() - timedelta(days=30)
            data_final = datetime.now()
            periodo = 'D'
        
        # Preparar parâmetros para cache
        tabela = st.session_state['usina']['tabela']
        is_multi_table = isinstance(tabela, dict)
        
        if is_multi_table:
            tabela = list(tabela.values())[0]
            # Para multi-tabela, buscar apenas colunas da UG01
            cols_energia_padrao = 'data_hora,energia_ug01'
        else:
            cols_energia_padrao = st.session_state['usina']['cols_energia']
        
        usina_nome = st.session_state['usina'].get('users', 'default')
        
        # Converter nomes padronizados para nomes reais
        mapeamento_energia = st.session_state['usina']['energia']
        cols_energia_real = convert_padronizado_to_real(cols_energia_padrao, mapeamento_energia, is_multi_table)
        
        data_inicial_str = data_inicial.strftime('%Y-%m-%d %H:%M:%S') if isinstance(data_inicial, datetime) else data_inicial
        data_final_str = data_final.strftime('%Y-%m-%d %H:%M:%S') if isinstance(data_final, datetime) else data_final
        
        # Usar cache
        data = _get_grafico_energia_cached(tabela, cols_energia_padrao, cols_energia_real, data_inicial_str, data_final_str, periodo, usina_nome)
        
        # Não precisa atualizar session state aqui - já temos os dados cached!
        # Removido get_db_data() desnecessário
        
        return data
    except Exception as e:
        get_error('get_grafico_energia, ln 217', e)

@st.cache_data(ttl=86400, show_spinner=False)  # Cache de 24 horas - colunas raramente mudam
def _get_names_all_columns_cached(tabela: str):
    """Função auxiliar com cache para nomes de colunas."""
    query = f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{tabela}'"
    result = st.session_state['db'].fetch_data(query)
    df = pd.DataFrame(result)
    df = tratamento_df(df)
    return df

@desempenho
def get_names_all_columns() -> pd.DataFrame:
    try:
        tabela = st.session_state['usina']['tabela']
        if isinstance(tabela, dict):
            tabela = list(tabela.values())[0]
        
        return _get_names_all_columns_cached(tabela)
    except Exception as e:
        get_error('get_names_all_columns, ln 210', e)
        return pd.DataFrame()

@desempenho
def fetch_dados_graficos(usina, colunas_selecionadas, data_hora_inicial, data_hora_final):
    try:
        # Determinar qual tabela usar
        if isinstance(usina['tabela'], dict):
            # Se tabela é um dicionário, usar a primeira tabela
            tabela_nome = list(usina['tabela'].values())[0]
        else:
            # Se tabela é uma string, usar diretamente
            tabela_nome = usina['tabela']
        
        colunas_sel = 'data_hora, '
        colunas_sel += ', '.join(colunas_selecionadas)
        query = f"SELECT {colunas_sel} FROM {tabela_nome} WHERE data_hora BETWEEN '{data_hora_inicial}' AND '{data_hora_final}'"
        print('query: ', query)
        result = st.session_state['db'].fetch_data(query)
        df = pd.DataFrame(result)
        df = tratamento_df(df)
        return df
    except Exception as e:
        get_error('fetch_dados_graficos, ln 220', e)

def fetch_dados_graficos_tabela(tabela_nome, colunas_selecionadas, data_hora_inicial, data_hora_final):
    try:       
        colunas_sel = 'data_hora, '
        colunas_sel += ', '.join(colunas_selecionadas)
        query = f"SELECT {colunas_sel} FROM {tabela_nome} WHERE data_hora BETWEEN '{data_hora_inicial}' AND '{data_hora_final}'"
        print('query: ', query)
        result = st.session_state['db'].fetch_data(query)
        df = pd.DataFrame(result)
        df = tratamento_df(df)
        return df
    except Exception as e:
        get_error('fetch_dados_graficos_tabela, ln 220', e)

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