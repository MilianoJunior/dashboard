'''
Como criar um projeto que descreve um dashboard com streamlit que se conecta em diferentes bancos de dados e mostra uma interface com filtros e gráficos, para CGH e PCH?
'''
import streamlit as st
import yaml
from dotenv import load_dotenv
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import plotly.express as px
import pandas as pd
from libs.componentes import create_energy_card
import math

from libs.db import (
    conectar_db, 
)
import os
import base64

# Inicializar session_state
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'load_data' not in st.session_state:
    st.session_state['load_data'] = False

# Configuração da página
st.set_page_config(
    page_title="EngeGOM",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Remove o botão Deploy e outros elementos do menu e ajusta o padding
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Remove espaço em branco no topo */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0rem !important;
        }
        
        /* Ajusta o header principal */
        [data-testid="stHeader"] {
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
        }
        
        /* Remove padding do container principal */
        .main > div {
            padding-top: 0rem !important;
        }
        
        /* Ajusta elementos dentro do header */
        .stTitle, .stHeader {
            margin-top: 0 !important;
            padding-top: 0 !important;
        }
        
        /* Remove padding do sidebar */
        [data-testid="stSidebar"] {
            padding-top: 0rem !important;
        }
        
        /* Ajusta o container do título */
        .css-1dp5vir {
            padding-top: 0 !important;
            margin-top: 0 !important;
        
        .main-container {
            border: 2px solid #00e1ff;
            border-radius: 15px;
            padding: 10px;
            margin: 5px;
        }
    </style>
""", unsafe_allow_html=True)

load_dotenv()

cont = 0
def desempenho(func):
    '''
    Decorator para medir o tempo de execução de uma função.
    '''
    import time
    def wrapper(*args, **kwargs):
        global cont
        cont += 1
        print(cont,f'função {func.__name__}: ','---' * 50)
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Tempo de execução: {end_time - start_time} segundos")
        print('---' * 50)
        return result
    return wrapper

deploy = True
if not deploy:
    with open("config/usuarios_usinas.yaml", "r") as file:
        config = yaml.safe_load(file)
else:
    url = os.getenv('MYSQLHOST')
    user = os.getenv('MYSQLUSER')
    password = os.getenv('MYSQLPASSWORD')
    database = os.getenv('MYSQLDATABASE')
    port = os.getenv('MYSQLPORT')
    with open("config/usuarios_usinas.yaml", "r") as file:
        config = yaml.safe_load(file)
    for usina in config['usinas']:
        config['usinas'][usina]['ip'] = url  # ok
        config['usinas'][usina]['usuario'] = user  # ok
        config['usinas'][usina]['senha'] = password  # ok
        config['usinas'][usina]['database'] = database  # ok
        config['usinas'][usina]['port'] = port  # ok

# variaveis de configuração
usinas = list(config['usinas'].keys())

# @desempenho
def login(config, usinas):
    # with st.container(border=True):
    st.title("EngeGOM - Login")
    usina = st.selectbox("Selecione a usina", usinas)
    usuario = st.text_input("Usuário", value="admin")
    senha = st.text_input("Senha", type="password", value="admin")
    login_btn = st.button("Login")
    if login_btn:
        if usuario == 'admin' and senha == 'admin':
            st.session_state['logado'] = True
            st.session_state['usina'] = config['usinas'][usina]
            st.session_state['load_data'] = False
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")

# @desempenho
def logout():
    st.session_state.clear()
    st.rerun()

# @desempenho
def menu_principal(config, usina):
    '''Menu principal do dashboard'''

    col1, col2, col3, col4 = st.columns([1, 6, 1, 4])
    with col1:
        st.image("assets/logo.png", width=100)
    with col2:
        st.markdown(f"<h2 style='text-align: left; margin-top: 0;'>Dashboard {st.session_state['usina']['tabela'].replace('_', ' ').capitalize()}</h2>", unsafe_allow_html=True)
    with col3:
        st.write(" ")
        logout_btn = st.button("Logout", use_container_width=True)
        if logout_btn:
            logout()

def get_error(e: Exception) -> str:
    '''
    Retorna uma mensagem de erro formatada com detalhes do traceback.
    '''
    import traceback
    
    error_info = traceback.extract_tb(e.__traceback__)[-1]
    file_name = error_info.filename.split('/')[-1]
    function_name = error_info.name  # Nome da função onde a exceção ocorreu
    
    return f"Erro na função {function_name} no arquivo {file_name}, linha {error_info.lineno}: {str(e)}"

# @desempenho
def get_db_data(query: str) -> pd.DataFrame:
    '''
    Executa uma query no banco de dados e retorna um DataFrame.
    
    Args:
        conexao: Objeto de conexão com o banco de dados
        query: String contendo a consulta SQL
        name_function: Nome da função chamadora (opcional)
    
    Returns:
        pd.DataFrame: DataFrame contendo os resultados da consulta
    '''
    cursor = None
    conexao = None
    try:
        conexao = conectar_db(st.session_state['usina']['ip'], 
                              st.session_state['usina']['usuario'], 
                              st.session_state['usina']['senha'], 
                              st.session_state['usina']['database'], 
                              st.session_state['usina']['port'])
        if not conexao:
            raise Exception('Conexão com o banco de dados falhou')
        cursor = conexao.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        colunas = [col[0] for col in cursor.description]

        return pd.DataFrame(result, columns=colunas)
    except Exception as e:
        print('get_db_data: ', e)
        error_message = get_error(e)
        st.error(error_message)
        raise Exception(error_message) from e
    finally:
        if cursor is not None:
            cursor.close()
        if conexao is not None:
            conexao.close()

# @desempenho
def get_info_usina(comando: str) -> str:
    '''
    Executa um comando no banco de dados e retorna a string da query SQL.
    '''
    try:
        energia = ', '.join(st.session_state['usina']['energia'].values())
        nivel = ', '.join(st.session_state['usina']['nivel'].values())
        data_inicial = datetime.now() - timedelta(days=30)
        data_inicial_180 = datetime.now() - timedelta(days=180)
        data_final = datetime.now()
        data_inicial_nivel = datetime.now() - timedelta(hours=1)
        data_final_nivel = datetime.now()
        comandos = {
            'energia total': f"SELECT {energia} FROM {st.session_state['usina']['tabela']} ORDER BY data_hora DESC LIMIT 1",
            'energia total 30 dias': f"SELECT {energia} FROM {st.session_state['usina']['tabela']} WHERE data_hora BETWEEN '{data_inicial}' AND '{data_final}'",
            'energia total 180 dias': f"SELECT {energia} FROM {st.session_state['usina']['tabela']} WHERE data_hora BETWEEN '{data_inicial_180}' AND '{data_final}'",
            'describe nivel': f"SELECT {nivel} FROM {st.session_state['usina']['tabela']} ORDER BY data_hora DESC LIMIT 60",
            'nivel': f"SELECT {nivel} FROM {st.session_state['usina']['tabela']} WHERE data_hora BETWEEN '{data_inicial_nivel}' AND '{data_final_nivel}'",
            'nome colunas': f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{st.session_state['usina']['tabela']}'",
        }
        return comandos[comando]
    except Exception as e:
        error_message = get_error(e)
        return error_message

# @desempenho
def get_total_gerado() -> pd.DataFrame:
    '''
    Calcula o total gerado de energia de uma usina para todas as unidades geradoras para todo o período;
    '''
    try:
        colunas_energia = list(st.session_state['usina']['energia'].values())
        query_energia = get_info_usina('energia total')
        data = get_db_data(query_energia)
        if data.empty:
            return pd.DataFrame(columns=['total'])
        data['total'] = data[[col for col in colunas_energia if 'energia' in col]].sum(axis=1)
        return data

    except Exception as e:
        error_message = get_error(e)
        # st.error(error_message)
        raise Exception(error_message) from e
    

# @desempenho
def calcular_energia_acumulada(df, colunas, periodo):
    """
    Calcula a energia acumulada diária ou mensal para as colunas de energia especificadas.

    Parâmetros:
    df (pd.DataFrame): DataFrame contendo os dados com uma coluna 'data_hora'.
    colunas (list): Lista de colunas de energia a serem processadas.
    periodo (str): 'D' para diário ou 'M' para mensal.

    Retorna:
    pd.DataFrame: DataFrame com as colunas de energia acumulada (ex.: 'prod_{col}').
    """
    # Validar período
    if periodo not in ['D', 'M']:
        raise ValueError("Período deve ser 'D' (diário) ou 'M' (mensal).")

    # Filtrar colunas de energia
    colunas_energia = [col for col in colunas if 'energia' in col]
    if not colunas_energia:
        raise ValueError("Nenhuma coluna de energia encontrada nas colunas fornecidas.")

    # Garantir que 'data_hora' é datetime
    df = df.copy()  # Evitar modificar o DataFrame original
    if not pd.api.types.is_datetime64_any_dtype(df['data_hora']):
        df['data_hora'] = pd.to_datetime(df['data_hora'])

    # Definir 'data_hora' como índice
    df = df.set_index('data_hora')

    # Mapear período para frequência de resampling
    freq = {'D': 'D', 'M': 'M'}
    
    # Agrupar pelo período e pegar o último valor
    df_resampled = df.resample(freq[periodo]).last()

    # Calcular diferenças para cada coluna de energia
    for col in colunas_energia:
        df_resampled[f'prod_{col}'] = df_resampled[col].diff()

    # Remover linhas com NaN nas colunas de produção
    df_resampled = df_resampled.dropna(subset=[f'prod_{col}' for col in colunas_energia])

    # Resetar o índice para ter 'data_hora' como coluna
    return df_resampled.reset_index()

# @desempenho
def get_ultimos_30_dias(periodo='D', janela=30) -> pd.DataFrame:
    '''
    Retorna os últimos 30 dias de dados da tabela de energia.
    '''
    try:
        colunas_energia = ', '.join(list(st.session_state['usina']['energia'].values()))
        data_inicial = datetime.now() - timedelta(days=janela)
        data_final = datetime.now()
        query = f"SELECT {colunas_energia} FROM {st.session_state['usina']['tabela']} WHERE data_hora BETWEEN '{data_inicial}' AND '{data_final}'"
        print('query: ', query)
        df = get_db_data(query)
        print('df: ', df)
        data = calcular_energia_acumulada(df, list(st.session_state['usina']['energia'].values()), periodo)
        return data
    except Exception as e:
        error_message = get_error(e)
        raise Exception(error_message) from e
    
def get_ultimos_180_dias_mensal() -> pd.DataFrame:
    '''
    Retorna os últimos 180 dias de dados da tabela de energia.
    '''
    try:
        # selecionar a ultima linha da colunas energia
        query = get_info_usina('energia total 180 dias')
        df = get_db_data(query)
        data = calcular_energia_acumulada(df, list(st.session_state['usina']['energia'].values()), 'M')
        # converter a coluna data_hora para o formato mes ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        data['data_hora'] = data['data_hora'].dt.strftime('%b')
        return data
    except Exception as e:
        error_message = get_error(e)
        raise Exception(error_message) from e
    
def get_names_all_columns() -> pd.DataFrame:
    '''
    Retorna o nome de todas as colunas da tabela do banco de dados.
    '''
    try:
        query = get_info_usina('nome colunas')
        df = get_db_data(query)
        return df
    except Exception as e:
        error_message = get_error(e)
        raise Exception(error_message) from e
    
def get_describe_nivel() -> pd.DataFrame:   
    '''
    Retorna o describe da tabela de energia.
    '''
    try:
        query = get_info_usina('describe nivel')
        df = get_db_data(query)
        colunas_nivel = [col for col in df.columns if 'nivel' in col]
        df = df[colunas_nivel].describe()
        return df
    except Exception as e:
        error_message = get_error(e)
        raise Exception(error_message) from e

def get_ultimos_1_hora_nivel() -> pd.DataFrame:
    '''
    Retorna os últimos 1 hora de dados da tabela de energia.
    '''
    try:
        query = get_info_usina('describe nivel')
        print('query: ', query)
        df = get_db_data(query)
        return df
    except Exception as e:
        error_message = get_error(e)
        raise Exception(error_message) from e

# @desempenho
def get_data_card_energia() -> dict:
    '''
        Card de energia
        - Calcula o total gerado de energia de uma usina para todas as unidades geradoras para todo o período;
        - filtra o valor máximo e mínimo de cada unidade geradora em um dia nos ultimos 30 dias;
        - calcula o percentual de geração em relação ao mês anterior;
        - retorna um dicionário com os valores.
    '''
    try:
        # selecionar a ultima linha da colunas energia
        energia_total = get_total_gerado()
        describe_nivel = get_describe_nivel()
        ultimos_180_dias = get_ultimos_180_dias_mensal()
        # inverter a ordem das colunas de ultimos_180_dias
        ultimos_180_dias = ultimos_180_dias[::-1]
        colunas_mensal = [col for col in ultimos_180_dias.columns if 'prod_' in col]
        list_cards = {}
        list_cards['Produção total'] = {
            'value': round(float(energia_total['total'].values[0]), 2),
            'value_max': None,
            'value_min': None,
            'percentual': None,
            'description': 'Produção total',
            'data_hora': energia_total['data_hora'][0].strftime('%d/%m/%Y %H:%M:%S'),
            'medida': 'MWh',
        }
        for col in describe_nivel.columns:
            list_cards[col.replace("_", " ").capitalize()] = {
                'value': round(float(describe_nivel.loc['mean', col]), 2),
                'value_max': round(float(describe_nivel.loc['max', col]), 2),
                'value_min': round(float(describe_nivel.loc['min', col]), 2),
                'percentual': round(float(describe_nivel.loc['std', col]), 2),
                'description': f'{col.replace("_", " ").capitalize()}',
                'data_hora': energia_total['data_hora'][0].strftime('%d/%m/%Y %H:%M:%S'),
                'medida': 'm',
            }
        for index, linha in ultimos_180_dias.iterrows():
            for i, col in enumerate(colunas_mensal):
                name_col = f'Engeria gerada - Mês {linha["data_hora"]}'
                list_cards[name_col] = {
                    'value': round(float(linha[col]), 2),
                    'value_max': None,
                    'value_min': None,
                    'percentual': None,
                    'description': f'Mês {linha["data_hora"]}',
                    'data_hora': energia_total['data_hora'][0].strftime('%d/%m/%Y %H:%M:%S'),
                    'medida': 'MWh',
                }
        return list_cards
    except Exception as e:
        error_message = get_error(e)
        # st.error(error_message)
        raise Exception(error_message) from e

def create_grafico_producao_energia(df):
    '''
    Cria um gráfico de produção de energia.
    '''
    # Filtrar apenas as colunas que começam com 'prod_'
    colunas_prod = [col for col in st.session_state.ultimos_30_dias.columns if col.startswith('prod_')]
    
    # Criar o gráfico com Plotly Express
    fig = px.bar(
        st.session_state.ultimos_30_dias,
        x='data_hora',
        y=colunas_prod,
        title='Produção de Energia',
        barmode='group',
        height=500
    )
    
    # Atualizar o layout
    fig.update_layout(
        xaxis_title='Data/Hora',
        yaxis_title='Energia (MWh)',
        legend_title='Unidades Geradoras'
    )
    
    # Exibir o gráfico
    st.plotly_chart(fig, use_container_width=True)

def create_grafico_nivel(df):
    '''
    Cria um gráfico de nível.
    '''
    colunas_nivel = [col for col in df.columns if 'nivel' in col]
    fig = px.line(df, x='data_hora', y=colunas_nivel, title='Nível')
    st.plotly_chart(fig, use_container_width=True)
    
# @desempenho
def carregar_dados(usina, periodo='M', janela=180):
    try:
        if periodo == 'Mensal':
            periodo = 'M'
        else:
            periodo = 'D'
        import time
        inicio = time.time()
        print('-'*100)
        print(' '*5, 'Cards')
        st.session_state.list_cards = get_data_card_energia()
        print(f'Tempo de execução: {time.time() - inicio} segundos')    
        print('-'*100)
        inicio = time.time()
        print(' '*5, 'Produção de energia')
        st.session_state.ultimos_30_dias = get_ultimos_30_dias(periodo, janela)
        print(f'Tempo de execução: {time.time() - inicio} segundos')
        print('-'*100)
        inicio = time.time()
        print(' '*5, 'Nível')
        st.session_state.ultimos_1_hora_nivel = get_ultimos_1_hora_nivel()
        print(f'Tempo de execução: {time.time() - inicio} segundos')
        
    except Exception as e:
        raise e
        print('carregar_dados: ', e)
    

# @desempenho
def set_load_data():
    st.session_state.load_data = True

# @desempenho
def layout(usina):
    '''Cards do dashboard'''

    st.sidebar.title('Configuração')
    periodo = st.sidebar.selectbox('Período', ['Diário', 'Mensal'])
    janela = st.sidebar.number_input('Janela em dias', value=30, min_value=1, max_value=365, step=1)
    btn_carregar = st.sidebar.button('Carregar', on_click=set_load_data)

    # Lógica para carregar os dados apenas quando o botão for clicado
    if st.session_state.load_data:
        st.session_state.stado = f"2- Dados carregados com período: {periodo} e janela: {janela}"
        carregar_dados(usina, periodo, janela)
        st.session_state.load_data = False
    else:
        if 'stado' not in st.session_state:
            st.session_state.stado = f"1 -Dados carregados com período: {periodo} e janela: {janela}"
            carregar_dados(usina, periodo, janela)
    
    col1, col2 = st.columns([5, 1.5])
    with col1:
        create_grafico_producao_energia(st.session_state.ultimos_30_dias)
        with st.expander('Informações'):
            st.write(st.session_state.ultimos_30_dias)
        create_grafico_nivel(st.session_state.ultimos_1_hora_nivel)
        with st.expander('Informações'):
            st.write(st.session_state.ultimos_1_hora_nivel)

    with col2:
        for i, (key, value) in enumerate(st.session_state.list_cards.items()):
            create_energy_card(key, value['value'], value['data_hora'], value['medida'], value['percentual'], value['value_max'], value['value_min'])

            
    # fazer um rodapé com as informações da usina
    st.divider()
    st.write(f'Usina: {usina["tabela"].replace("_", " ").capitalize()}')
    st.write('EngeSEP - Engenharia integrada de sistemas')
    st.write(f'Atualizado em: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}')


# try:
if st.session_state['logado']:
    menu_principal(config, st.session_state['usina'])
    layout(st.session_state['usina'])
else:
    login(config, usinas)
# except Exception as e:
#     st.error(f'Erro: {e}')











# Como criar um projeto que descreve um dashboard com streamlit que se conecta em diferentes bancos de dados e mostra uma interface com filtros e gráficos, para CGH e PCH?
# '''
# import streamlit as st
# import yaml
# from dotenv import load_dotenv
# from datetime import datetime, timedelta
# import streamlit.components.v1 as components
# import plotly.express as px
# import pandas as pd

# from libs.db import (
#     conectar_db, 
#     read_where_data, 
#     columns_table, 
#     dados, 
#     total_gerado,
# )
# from libs.componentes import (
#     create_energy_card,
# )
# import os
# import base64

# # Inicializar session_state
# if 'logado' not in st.session_state:
#     st.session_state['logado'] = False
# if 'load_data' not in st.session_state:
#     st.session_state['load_data'] = False

# # Configuração da página
# st.set_page_config(
#     page_title="EngeGOM",
#     page_icon="🧊",
#     layout="wide",
#     initial_sidebar_state="expanded",
# )

# # Remove o botão Deploy e outros elementos do menu e ajusta o padding
# st.markdown("""
#     <style>
#         #MainMenu {visibility: hidden;}
#         footer {visibility: hidden;}
#         header {visibility: hidden;}
        
#         /* Remove espaço em branco no topo */
#         .block-container {
#             padding-top: 1rem !important;
#             padding-bottom: 0rem !important;
#         }
        
#         /* Ajusta o header principal */
#         [data-testid="stHeader"] {
#             padding-top: 0rem !important;
#             padding-bottom: 0rem !important;
#         }
        
#         /* Remove padding do container principal */
#         .main > div {
#             padding-top: 0rem !important;
#         }
        
#         /* Ajusta elementos dentro do header */
#         .stTitle, .stHeader {
#             margin-top: 0 !important;
#             padding-top: 0 !important;
#         }
        
#         /* Remove padding do sidebar */
#         [data-testid="stSidebar"] {
#             padding-top: 0rem !important;
#         }
        
#         /* Ajusta o container do título */
#         .css-1dp5vir {
#             padding-top: 0 !important;
#             margin-top: 0 !important;
        
#         .main-container {
#             border: 2px solid #00e1ff;
#             border-radius: 15px;
#             padding: 10px;
#             margin: 5px;
#         }
#     </style>
# """, unsafe_allow_html=True)

# load_dotenv()

# deploy = False
# if not deploy:
#     print('Carregando configurações do arquivo: False')
#     with open("config/usuarios_usinas.yaml", "r") as file:
#         config = yaml.safe_load(file)
# else:
#     print('Carregando configurações do ambiente: True')
#     url = os.getenv('MYSQLHOST')
#     user = os.getenv('MYSQLUSER')
#     password = os.getenv('MYSQLPASSWORD')
#     database = os.getenv('MYSQLDATABASE')
#     port = os.getenv('MYSQLPORT')
#     with open("config/usuarios_usinas.yaml", "r") as file:
#         config = yaml.safe_load(file)
#     for usina in config['usinas']:
#         config['usinas'][usina]['ip'] = url  # ok
#         config['usinas'][usina]['usuario'] = user  # ok
#         config['usinas'][usina]['senha'] = password  # ok
#         config['usinas'][usina]['database'] = database  # ok
#         config['usinas'][usina]['port'] = port  # ok

# # variaveis de configuração
# usinas = list(config['usinas'].keys())

# def login(config, usinas):
#     # with st.container(border=True):
#     st.title("EngeGOM - Login")
#     usina = st.selectbox("Selecione a usina", usinas)
#     usuario = st.text_input("Usuário", value="admin")
#     senha = st.text_input("Senha", type="password", value="admin")
#     login_btn = st.button("Login")
#     if login_btn:
#         if usuario == 'admin' and senha == 'admin':
#             st.session_state['logado'] = True
#             st.session_state['usina'] = usina
#             st.session_state['load_data'] = False
#             st.rerun()
#         else:
#             st.error("Usuário ou senha inválidos")

# def logout():
#     st.session_state.clear()
#     st.rerun()

# def menu_principal(config, usina):
#     '''Menu principal do dashboard'''

#     col1, col2, col3, col4 = st.columns([1, 6, 1, 4])
#     with col1:
#         st.image("assets/logo.png", width=100)
#     with col2:
#         st.markdown(f"<h2 style='text-align: left; margin-top: 0;'>Dashboard {usina}</h2>", unsafe_allow_html=True)
#     with col3:
#         st.write(" ")
#         logout_btn = st.button("Logout", use_container_width=True)
#         if logout_btn:
#             logout()

# def get_data_card_energia(conexao, colunas_energia):
#     # crian um cursor para a conexão
#     cursor = conexao.cursor()
#     # selecionar a ultima linha da colunas energia
#     columns = ', '.join(colunas_energia)
#     cursor.execute(f"SELECT {columns} FROM {usina['tabela']} ORDER BY data_hora DESC LIMIT 1")
#     energia_total = cursor.fetchall()
#     cursor.close()
#     energia_total = pd.DataFrame(energia_total, columns=colunas_energia)
#     # somar os valores das colunas energia
#     energia_total['total'] = energia_total[colunas_energia].sum(axis=1)
#     dict_return = {
#             'Produção total': {
#                 'value': round(float(energia_total['total'].values[0]), 2),
#                 'value_max': None,
#                 'value_min': None,
#                 'percentual': None,
#                 'description': 'Produção total',
#                 'data_hora': energia_total['data_hora'][0].strftime('%d/%m/%Y %H:%M:%S'),
#                 'medida': 'MWh',
#             },
#         }
#     return dict_return

# def carregar_dados(usina, periodo='M', janela=180):
#     try:
#         conexao = conectar_db(usina['ip'], usina['usuario'], usina['senha'], usina['database'], usina['port'])
#         if not conexao is None:
#             colunas_energia = list(usina['energia'].values())
#             colunas_nivel = list(usina['nivel'].values())
#             # st.sidebar.write(usina)
#             # cursor = conexao.cursor()
#             # # selecionar as 10 ultimas linhas da tabela
#             # cursor.execute(f"SELECT * FROM {usina['tabela']} ORDER BY data_hora DESC LIMIT 10")
#             # df = cursor.fetchall()
#             # colunas = [i[0] for i in cursor.description]
#             # df = pd.DataFrame(df, columns=colunas)
#             # st.write(df)
#             # cursor.close()
#             # dict_return = get_data_card_energia(conexao, colunas_energia)
#             # st.write(dict_return)
#             if periodo == 'Mensal':
#                 periodo = 'M'
#             else:
#                 periodo = 'D'

#             energia_total, nivel, describe_nivel, energia_mensal, dict_return = dados(conexao, usina['tabela'], colunas_energia, colunas_nivel, periodo, janela)
#             # st.write('energia_total')
#             # st.write(energia_total)
#             # st.write('nivel')
#             # st.write(nivel)
#             # st.write('describe_nivel')
#             # st.write(describe_nivel)
#             # st.write('energia_mensal')
#             # st.write(energia_mensal)
#             # st.write('dict_return')
#             st.write(dict_return)
#             if periodo == 'D':
#                 energia_mensal['data_hora'] = energia_mensal['data_hora'].dt.strftime('%Y-%m-%d')
#             else:
#                 energia_mensal['data_hora'] = energia_mensal['data_hora'].dt.strftime('%Y-%m')
#             energia_mensal = energia_mensal.set_index('data_hora')
#             colunas_energia = [col for col in colunas_energia if 'energia' in col]
#             energia_mensal = energia_mensal.drop(columns=colunas_energia)
#             nivel = nivel.set_index('data_hora')
#             st.session_state.energia_total = energia_total
#             st.session_state.nivel = nivel
#             st.session_state.describe_nivel = describe_nivel
#             st.session_state.energia_mensal = energia_mensal
#             st.session_state.dict_return = dict_return

#             # carregar todas as colunas da tabela do banco de dados
#             colunas = columns_table(conexao, usina['tabela'])
#             # colunas = colunas.drop(columns=['id'])
#             colunas = colunas['Field'].tolist()
#             if 'id' in colunas:
#                 colunas.remove('id')
#             st.session_state.colunas = colunas
#         else:
#             st.error('Erro ao conectar ao banco de dados')
#     except Exception as e:
#         st.session_state.energia_total = pd.DataFrame()
#         st.session_state.nivel = pd.DataFrame()
#         st.session_state.describe_nivel = pd.DataFrame()
#         st.session_state.energia_mensal = pd.DataFrame()
#         st.session_state.dict_return = {}
#         st.session_state.colunas = []
    
# def carregar_dados_selecionados(usina, colunas_selecionadas, tempo_inicial, tempo_final):
#     try:
#         conexao = conectar_db(usina['ip'], usina['usuario'], usina['senha'], usina['database'], usina['port'])
#         df = read_where_data(conexao, usina['tabela'], tempo_inicial, tempo_final, colunas_selecionadas)
#         return df
#     except Exception as e:
#         return pd.DataFrame(columns=colunas_selecionadas)

# # Função para definir que os dados devem ser carregados
# def set_load_data():
#     st.session_state.load_data = True

# def layout(usina):
#     '''Cards do dashboard'''

#     st.sidebar.title('Configuração')
#     periodo = st.sidebar.selectbox('Período', ['Diário', 'Mensal'])
#     janela = st.sidebar.number_input('Janela em dias', value=30, min_value=1, max_value=365, step=1)
#     btn_carregar = st.sidebar.button('Carregar', on_click=set_load_data)
    
#     # Lógica para carregar os dados apenas quando o botão for clicado
#     if st.session_state.load_data:
#         st.session_state.stado = f"Dados carregados com período: {periodo} e janela: {janela}"
#         carregar_dados(usina, periodo, janela)
#         st.session_state.load_data = False
#     else:
#         if 'stado' not in st.session_state:
#             st.session_state.stado = f"Dados carregados com período: {periodo} e janela: {janela}"
#             carregar_dados(usina, periodo, janela)
    
#     st.write(st.session_state.stado)
#     colunas_energia = list(usina['energia'].values())
#     colunas_nivel = list(usina['nivel'].values())

#     energia_total = st.session_state.energia_total
#     nivel = st.session_state.nivel
#     describe_nivel = st.session_state.describe_nivel
#     energia_mensal = st.session_state.energia_mensal
#     dict_return = st.session_state.dict_return
#     colunas = st.session_state.colunas

#     # Verifica se há dados para exibir
#     if len(dict_return) > 0:
#         cols = st.columns(len(dict_return))
#         for i, (key, value) in enumerate(dict_return.items()):
#             with cols[i]:
#                 create_energy_card(key, value['value'], value['data_hora'], value['medida'], value['percentual'], value['value_max'], value['value_min'])
#     else:
#         st.warning("Nenhum dado de energia disponível para exibição.")

#     col1, col2 = st.columns(2)
#     with col1:
#         with st.container(border=True):
#             periodo_text = 'Período: ' + periodo if periodo == 'Mensal' else 'Período: ' + periodo + ' dias'
#             st.bar_chart(energia_mensal, stack=False, height=500) 
#         with st.expander('Energia Produzida' + periodo_text):
#             st.write(energia_mensal)
#     with col2:
#         with st.container(border=True):
#             st.write('Nível de água: as ultimas 24 horas')
#             fig = px.line(
#                     nivel,
#                     x=nivel.index,
#                     y=colunas_nivel[1::],
#                     labels={'value': 'Nível de Água', 'variable': 'Tipo de Nível', 'data_hora': 'Data'}
#                 )
#             fig.update_layout(height=500)
#             st.plotly_chart(fig, use_container_width=True)
#         with st.expander('Nível de água'):
#             st.write(nivel)

#     st.divider()
#     # criar 3 entradas para selecionar as colunas da tabela o tempo inicial e o tempo final
#     col1, col2, col3, col4 = st.columns(4)
#     with col1:
#         colunas_selecionadas = st.multiselect('Colunas', st.session_state.colunas)
#     with col2:
#         tempo_inicial = st.date_input('Tempo inicial', value=datetime.now() - timedelta(days=30))
#     with col3:
#         tempo_final = st.date_input('Tempo final', value=datetime.now())
#     with col4:
#         st.write(' ')
#         st.write(' ')
#         btn_carregar_dados = st.button('Carregar dados')

#     # criar um botão para carregar os dados
#     if btn_carregar_dados:
#         colunas_selecionadas.append('data_hora')
#         df = carregar_dados_selecionados(usina, colunas_selecionadas, tempo_inicial, tempo_final)

#         # setar o index como data_hora
#         df = df.set_index('data_hora')
#         df = df.sort_index()
#         colunas_selecionadas.remove('data_hora')

#         # criar um gráfico de linha para cada coluna selecionada
#         for coluna in colunas_selecionadas:
#             st.write(coluna.replace('_', ' ').capitalize())
#             fig = px.line(df, x=df.index, y=coluna)
#             st.plotly_chart(fig, use_container_width=True)
    
#         with st.expander('Dados selecionados'):
#             st.write(df)
            
#     # fazer um rodapé com as informações da usina
#     st.divider()
#     st.write(f'Usina: {usina["tabela"].replace("_", " ").capitalize()}')
#     st.write('EngeSEP - Engenharia integrada de sistemas')
#     st.write(f'Atualizado em: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}')

# # try:
# if st.session_state['logado']:
#     menu_principal(config, st.session_state['usina'])
#     layout(config['usinas'][st.session_state['usina']])
# else:
#     login(config, usinas)
# # except Exception as e:
# #     st.error(f'Erro: {e}')

