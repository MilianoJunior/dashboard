import streamlit as st
import yaml
from dotenv import load_dotenv
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import plotly.express as px
import pandas as pd
from libs.componentes import (create_energy_card, 
                              create_widget_temperatura, 
                              menu_principal, 
                              create_grafico_producao_energia, 
                              create_grafico_nivel)
import plotly.graph_objects as go
import math
import os
import base64
from libs.db import (
    conectar_db, 
    desempenho
)
import os
import base64

deploy = True

if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'load_data' not in st.session_state:
    st.session_state['load_data'] = False

st.set_page_config(
    page_title="EngeGOM",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0rem !important;
        }
        [data-testid="stHeader"] {
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
        }
        .main > div {
            padding-top: 0rem !important;
        }
        .stTitle, .stHeader {
            margin-top: 0 !important;
            padding-top: 0 !important;
        }
        [data-testid="stSidebar"] {
            padding-top: 0rem !important;
        }
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

def get_error(name, e: Exception) -> str:
    import traceback
    error_info = traceback.extract_tb(e.__traceback__)[-1]
    file_name = error_info.filename.split('/')[-1]
    function_name = error_info.name
    st.error(f"Erro na função {name} - {function_name} no arquivo {file_name}, linha {error_info.lineno}: {str(e)}")
    if st.button('Voltar'):
        st.session_state.clear()
        st.rerun()
    st.stop()

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
        config['usinas'][usina]['ip'] = url
        config['usinas'][usina]['usuario'] = user
        config['usinas'][usina]['senha'] = password
        config['usinas'][usina]['database'] = database
        config['usinas'][usina]['port'] = port

usinas = list(config['usinas'].keys())

def logout():
    st.session_state.clear()
    st.rerun()

@desempenho
def get_db_data(query: str) -> pd.DataFrame:
    cursor = None
    if 'conexao' not in st.session_state:
        st.session_state['conexao'] = conectar_db(st.session_state['usina']['ip'], 
                                st.session_state['usina']['usuario'], 
                                st.session_state['usina']['senha'], 
                                st.session_state['usina']['database'], 
                                st.session_state['usina']['port'])
    try:
        if not st.session_state['conexao']:
            raise Exception('Conexão com o banco de dados falhou')
        cursor = st.session_state['conexao'].cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        colunas = [col[0] for col in cursor.description]
        df_ = pd.DataFrame(result, columns=colunas)
        # Remove colunas que ainda são object e não são data_hora
        for col in df_.dtypes.index:
            if df_[col].dtype != 'int64' and df_[col].dtype != 'float64' and col != 'data_hora':
                # df_.drop(columns=[col], inplace=True)
                # verifica se a coluna é numerica
                if pd.to_numeric(df_[col], errors='coerce').notna().all():
                    # converte todos os valores para float
                    df_[col] = df_[col].astype(float)
                    print('#####'*10)
                    print('Numerica')
                    print( ' '*10,col, df_[col].dtype)
                    print('#####'*10)
                else:
                    print('#####'*10)
                    print('Não Numerica')
                    print( ' '*10,col, df_[col].dtype)
                    print('#####'*10)
        return df_
    except Exception as e:
        get_error('get_db_data, ln 126', e)

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
def get_total_gerado() -> pd.DataFrame:
    try:
        colunas_energia = list(st.session_state['usina']['energia'].values())
        query_energia = get_info_usina('energia total')
        data = get_db_data(query_energia)
        if data.empty:
            return pd.DataFrame(columns=['total'])
        data['total'] = data[[col for col in colunas_energia if 'energia' in col]].sum(axis=1)
        return data
    except Exception as e:
        get_error('get_total_gerado, ln 160', e)

@desempenho
def calcular_energia_acumulada(df, colunas, periodo):
    try:
        colunas_energia = [col for col in colunas if 'energia' in col]
        df = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df['data_hora']):
            df['data_hora'] = pd.to_datetime(df['data_hora'])
        df = df.set_index('data_hora')
        freq = {'D': 'D', 'M': 'ME'}
        df_resampled = df.resample(freq[periodo]).last()
        print('#####'*10)
        print('df_resampled: ', periodo)
        print(df_resampled)
        print('#####'*10)
        # substituir os valores negativos por 0
        df_resampled = df_resampled.apply(lambda x: x.clip(lower=0))
        for col in colunas_energia:
            df_resampled[f'prod_{col}'] = df_resampled[col].diff()
        # Remover linhas com NaN nas colunas de produção
        prod_cols = [f'prod_{col}' for col in colunas_energia]
        df_resampled = df_resampled.dropna(subset=prod_cols)
        # Remover valores negativos nas colunas de produção
        for prod_col in prod_cols:
            df_resampled = df_resampled[df_resampled[prod_col] >= 0]
        return df_resampled.reset_index()
    except Exception as e:
        get_error('calcular_energia_acumulada, ln 183', e)

@desempenho
def get_ultimos_30_dias(periodo='D', janela=30) -> pd.DataFrame:
    try:
        colunas_energia = ', '.join(list(st.session_state['usina']['energia'].values()))
        data_inicial = datetime.now() - timedelta(days=janela)
        data_final = datetime.now()
        query = f"SELECT {colunas_energia} FROM {st.session_state['usina']['tabela']} WHERE data_hora BETWEEN '{data_inicial}' AND '{data_final}'"
        df = get_db_data(query)
        data = calcular_energia_acumulada(df, list(st.session_state['usina']['energia'].values()), periodo)
        return data
    except Exception as e:
        get_error('get_ultimos_30_dias, ln 190', e)

@desempenho
def get_ultimos_180_dias_mensal() -> pd.DataFrame:
    try:
        query = get_info_usina('energia total 180 dias')
        df = get_db_data(query)
        data = calcular_energia_acumulada(df, list(st.session_state['usina']['energia'].values()), 'M')
        print('#####'*10)
        print('get data 180 dias')
        print(data)
        print('#####'*10)
        # Formatar os meses em português do Brasil
        # meses_pt = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        # data['data_hora'] = data['data_hora'].dt.month.apply(lambda x: meses_pt[x-1])
        # se existir valor negativo, trocar para 0
        cols_energia = list(st.session_state['usina']['energia'].values())
        # Garante que só as colunas de energia serão afetadas
        data[cols_energia] = data[cols_energia].apply(pd.to_numeric, errors='coerce').clip(lower=0)
        # Converter para datetime antes de acessar .dt
        if not pd.api.types.is_datetime64_any_dtype(data['data_hora']):
            data['data_hora'] = pd.to_datetime(data['data_hora'], errors='coerce')
        meses_pt = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        data['data_hora'] = data['data_hora'].dt.month.apply(lambda x: meses_pt[x-1])
        return data
    except Exception as e:
        get_error('get_ultimos_180_dias_mensal, ln 205', e)

@desempenho
def get_names_all_columns() -> pd.DataFrame:
    try:
        query = get_info_usina('nome colunas')
        df = get_db_data(query)
        return df
    except Exception as e:
        get_error('get_names_all_columns, ln 210', e)

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

@desempenho
def get_ultimos_1_hora_nivel() -> pd.DataFrame:
    try:
        query = get_info_usina('describe nivel')
        df = get_db_data(query)
        return df
    except Exception as e:
        get_error('get_ultimos_1_hora_nivel, ln 235', e)

@desempenho
def get_data_card_energia() -> dict:
    try:
        energia_total = get_total_gerado()
        # describe_nivel = get_describe_nivel()
        ultimos_180_dias = get_ultimos_180_dias_mensal()
        colunas_mensal = [col for col in ultimos_180_dias.columns if 'prod_' in col]
        ultimos_180_dias['total'] = ultimos_180_dias[colunas_mensal].sum(axis=1)
        ultimos_180_dias['percentual'] = ultimos_180_dias['total'].pct_change(periods=1) * 100
        ultimos_180_dias = ultimos_180_dias[::-1]
        print('#####'*10)
        print('ultimos_180_dias')
        print(ultimos_180_dias)
        print('#####'*10)
        if 'last_update' not in st.session_state:
            st.session_state.last_update = energia_total['data_hora'][0].strftime('%d/%m/%Y %H:%M:%S')
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
        # for col in describe_nivel.columns:
        #     list_cards[col.replace("_", " ").capitalize()] = {
        #         'value': round(float(describe_nivel.loc['mean', col]), 2),
        #         'value_max': round(float(describe_nivel.loc['max', col]), 2),
        #         'value_min': round(float(describe_nivel.loc['min', col]), 2),
        #         'percentual': round(float(describe_nivel.loc['std', col]), 2),
        #         'description': f'{col.replace("_", " ").capitalize()}',
        #         'data_hora': energia_total['data_hora'][0].strftime('%d/%m/%Y %H:%M:%S'),
        #         'medida': 'm',
        #     }
        for index, linha in ultimos_180_dias.iterrows():
            name_col = f'Engeria gerada - Mês {linha["data_hora"]}'
            list_cards[name_col] = {
                'value': round(float(linha['total']), 2),
                'value_max': None,
                'value_min': None,
                'percentual': round(float(linha['percentual']), 2) if pd.notnull(linha['percentual']) else None,
                'description': f'Mês {linha["data_hora"]}',
                'data_hora': energia_total['data_hora'][0].strftime('%d/%m/%Y %H:%M:%S'),
                'medida': 'MWh',
            }
        return list_cards
    except Exception as e:
        get_error(e)

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
        get_error(e)

@desempenho
def carregar_dados(usina, periodo='M', janela=180):
    try:
        if periodo == 'Mensal':
            periodo = 'M'
        else:
            periodo = 'D'
        st.session_state.list_cards = get_data_card_energia()
        st.session_state.ultimos_30_dias = get_ultimos_30_dias(periodo, janela)
        st.session_state.ultimos_1_hora_nivel = get_ultimos_1_hora_nivel()
        st.session_state.temperatura = get_temperatura()
    except Exception as e:
        get_error(e)

@desempenho
def set_load_data():
    st.session_state.load_data = True

@desempenho
def layout(usina):
    st.sidebar.title('Configuração')
    periodo = st.sidebar.selectbox('Período', ['Diário', 'Mensal'])
    janela = st.sidebar.number_input('Janela em dias', value=30, min_value=1, max_value=365, step=1)
    btn_carregar = st.sidebar.button('Carregar', on_click=set_load_data)
    if st.session_state.load_data:
        st.session_state.stado = f"2- Dados carregados com período: {periodo} e janela: {janela}"
        carregar_dados(usina, periodo, janela)
        st.session_state.load_data = False
        st.sidebar.write('Atualizado em: ', st.session_state.last_update)
    else:
        if 'stado' not in st.session_state:
            st.session_state.stado = f"1 -Dados carregados com período: {periodo} e janela: {janela}"
            carregar_dados(usina, periodo, janela)
            st.sidebar.write('Atualizado em: ', st.session_state.last_update)
    col1, col2 = st.columns([5, 1.5])
    with col1:
        create_grafico_producao_energia(st.session_state.ultimos_30_dias)
        with st.expander('Informações'):
            st.write(st.session_state.ultimos_30_dias)
        create_grafico_nivel(st.session_state.ultimos_1_hora_nivel)
        with st.expander('Informações'):
            st.write(st.session_state.ultimos_1_hora_nivel)
        create_widget_temperatura(st.session_state.temperatura)
    with col2:
        for i, (key, value) in enumerate(st.session_state.list_cards.items()):
            create_energy_card(key, value['value'], value['data_hora'], value['medida'], value['percentual'], value['value_max'], value['value_min'])
    with st.container(border=True):
        colunas = get_names_all_columns()
        cols1, cols2, col3, col4 = st.columns(4)
        with cols1:
            colunas_selecionadas = st.multiselect('Selecione as colunas', colunas['COLUMN_NAME'].tolist(), default=colunas['COLUMN_NAME'].tolist()[1])
        with cols2:
            data_hora_inicial = st.date_input('Data inicial', value=datetime.now() - timedelta(days=30))
        with col3:
            data_hora_final = st.date_input('Data final', value=datetime.now())
        with col4:
            st.write('')
            st.write('')
            btn_grafico = st.button('Carregar gráficos')
        if btn_grafico:
            columns_query = ', '.join(colunas_selecionadas)
            query = f"SELECT {'data_hora,'+ columns_query} FROM {usina['tabela']} WHERE data_hora BETWEEN '{data_hora_inicial}' AND '{data_hora_final}'"
            df = get_db_data(query)
            df['data_hora'] = pd.to_datetime(df['data_hora'])
            df = df.set_index('data_hora')
            df_original = df.copy()
            df_normalized = df.copy()
            df_normalized[colunas_selecionadas] = df_normalized[colunas_selecionadas].apply(
                lambda x: (x - x.mean()) / x.std())
            tab1, tab2 = st.tabs(["Dados Originais", "Dados Normalizados"])
            with tab1:
                st.subheader("Gráfico de Dados Originais")
                st.line_chart(df_original[colunas_selecionadas])
                with st.expander('Informações dos Dados Originais'):
                    st.write(df_original)
            with tab2:
                st.subheader("Gráfico de Dados Normalizados")
                st.line_chart(df_normalized[colunas_selecionadas])
                with st.expander('Informações dos Dados Normalizados'):
                    st.write(df_normalized)
    st.divider()
    st.write(f'Usina: {usina["tabela"].replace("_", " ").capitalize()}')
    st.write('EngeSEP - Engenharia integrada de sistemas')
    st.write(f'Atualizado em: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}')
    if st.session_state['conexao']:
        st.session_state['conexao'].close()

@desempenho
def login(config, usinas):
    try:
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
                print('Logado')
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos")
    except Exception as e:
        get_error(e)

if st.session_state['logado']:
    menu_principal(config, st.session_state['usina'])
    layout(st.session_state['usina'])
else:
    login(config, usinas)

'''
1 -Demora: 18.02209973335266 s
2- Demora: 9.437216520309448 s
'''