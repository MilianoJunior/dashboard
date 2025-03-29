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

from libs.db import (
    conectar_db, 
    read_where_data, 
    columns_table, 
    dados, 
)
from libs.componentes import (
    create_energy_card,
    criar_grafico_nivel
)
import os
import base64

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
# Inicializar session_state
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

# Carregar configurações
with open("config/usuarios_usinas.yaml", "r") as file:
    config = yaml.safe_load(file)

# variaveis de configuração
usinas = list(config['usinas'].keys())

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
            st.session_state['usina'] = usina
            st.session_state['load_data'] = False
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")

def logout():
    st.session_state.clear()
    st.rerun()

def menu_principal(config, usina):
    '''Menu principal do dashboard'''

    col1, col2, col3, col4 = st.columns([1, 6, 1, 4])
    with col1:
        st.image("assets/logo.png", width=100)
    with col2:
        st.markdown(f"<h2 style='text-align: left; margin-top: 0;'>Dashboard {usina}</h2>", unsafe_allow_html=True)
    with col3:
        st.write(" ")
        logout_btn = st.button("Logout", use_container_width=True)
        if logout_btn:
            logout()

def carregar_dados(usina, periodo='M', janela=180):
    conexao = conectar_db(usina['ip'], usina['usuario'], usina['senha'], usina['database'], usina['port'])
    if not conexao is None:
        colunas_energia = list(usina['energia'].values())
        colunas_nivel = list(usina['nivel'].values())
        if periodo == 'Mensal':
            periodo = 'M'
        else:
            periodo = 'D'
        energia_total, nivel, describe_nivel, energia_mensal, dict_return = dados(conexao, usina['tabela'], colunas_energia, colunas_nivel, periodo, janela)
        if periodo == 'D':
            energia_mensal['data_hora'] = energia_mensal['data_hora'].dt.strftime('%Y-%m-%d')
        else:
            energia_mensal['data_hora'] = energia_mensal['data_hora'].dt.strftime('%Y-%m')
        energia_mensal = energia_mensal.set_index('data_hora')
        colunas_energia = [col for col in colunas_energia if 'energia' in col]
        energia_mensal = energia_mensal.drop(columns=colunas_energia)
        nivel = nivel.set_index('data_hora')
        st.session_state.energia_total = energia_total
        st.session_state.nivel = nivel
        st.session_state.describe_nivel = describe_nivel
        st.session_state.energia_mensal = energia_mensal
        st.session_state.dict_return = dict_return

        # carregar todas as colunas da tabela do banco de dados
        colunas = columns_table(conexao, usina['tabela'])
        # colunas = colunas.drop(columns=['id'])
        colunas = colunas['Field'].tolist()
        if 'id' in colunas:
            colunas.remove('id')
        st.session_state.colunas = colunas
    else:
        st.error('Erro ao conectar ao banco de dados')
    
def carregar_dados_selecionados(usina, colunas_selecionadas, tempo_inicial, tempo_final):
    conexao = conectar_db(usina['ip'], usina['usuario'], usina['senha'], usina['database'], usina['port'])
    df = read_where_data(conexao, usina['tabela'], tempo_inicial, tempo_final, colunas_selecionadas)
    return df

# Função para definir que os dados devem ser carregados
def set_load_data():
    st.session_state.load_data = True

def layout(usina):
    '''Cards do dashboard'''

    st.sidebar.title('Configuração')
    periodo = st.sidebar.selectbox('Período', ['Diário', 'Mensal'])
    janela = st.sidebar.number_input('Janela em dias', value=30, min_value=1, max_value=365, step=1)
    btn_carregar = st.sidebar.button('Carregar', on_click=set_load_data)
    
    # Lógica para carregar os dados apenas quando o botão for clicado
    if st.session_state.load_data:
        st.session_state.stado = f"Dados carregados com período: {periodo} e janela: {janela}"
        carregar_dados(usina, periodo, janela)
        st.session_state.load_data = False
    else:
        if 'stado' not in st.session_state:
            st.session_state.stado = f"Dados carregados com período: {periodo} e janela: {janela}"
            carregar_dados(usina, periodo, janela)
    
    st.write(st.session_state.stado)
    colunas_energia = list(usina['energia'].values())
    colunas_nivel = list(usina['nivel'].values())

    energia_total = st.session_state.energia_total
    nivel = st.session_state.nivel
    describe_nivel = st.session_state.describe_nivel
    energia_mensal = st.session_state.energia_mensal
    dict_return = st.session_state.dict_return
    colunas = st.session_state.colunas

    cols = st.columns(len(dict_return))
    for i, (key, value) in enumerate(dict_return.items()):
        with cols[i]:
            create_energy_card(key, value['value'], value['data_hora'], value['medida'], value['percentual'], value['value_max'], value['value_min'])

    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            periodo_text = 'Período: ' + periodo if periodo == 'Mensal' else 'Período: ' + periodo + ' dias'
            st.bar_chart(energia_mensal, stack=False, height=500) 
        with st.expander('Energia Produzida' + periodo_text):
            st.write(energia_mensal)
    with col2:
        with st.container(border=True):
            st.write('Nível de água: as ultimas 24 horas')
            fig = px.line(
                    nivel,
                    x=nivel.index,
                    y=colunas_nivel[1::],
                    labels={'value': 'Nível de Água', 'variable': 'Tipo de Nível', 'data_hora': 'Data'}
                )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
        with st.expander('Nível de água'):
            st.write(nivel)

    st.divider()
    # criar 3 entradas para selecionar as colunas da tabela o tempo inicial e o tempo final
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        colunas_selecionadas = st.multiselect('Colunas', st.session_state.colunas)
    with col2:
        tempo_inicial = st.date_input('Tempo inicial', value=datetime.now() - timedelta(days=30))
    with col3:
        tempo_final = st.date_input('Tempo final', value=datetime.now())
    with col4:
        st.write(' ')
        st.write(' ')
        btn_carregar_dados = st.button('Carregar dados')

    # criar um botão para carregar os dados
    if btn_carregar_dados:
        colunas_selecionadas.append('data_hora')
        df = carregar_dados_selecionados(usina, colunas_selecionadas, tempo_inicial, tempo_final)

        # setar o index como data_hora
        df = df.set_index('data_hora')
        df = df.sort_index()
        colunas_selecionadas.remove('data_hora')

        # criar um gráfico de linha para cada coluna selecionada
        for coluna in colunas_selecionadas:
            st.write(coluna.replace('_', ' ').capitalize())
            fig = px.line(df, x=df.index, y=coluna)
            st.plotly_chart(fig, use_container_width=True)
    
        with st.expander('Dados selecionados'):
            st.write(df)
            
    # fazer um rodapé com as informações da usina
    st.divider()
    st.write(f'Usina: {usina["tabela"].replace("_", " ").capitalize()}')
    st.write('EngeSEP - Engenharia integrada de sistemas')
    st.write(f'Atualizado em: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}')


if st.session_state['logado']:
    menu_principal(config, st.session_state['usina'])
    layout(config['usinas'][st.session_state['usina']])
else:
    login(config, usinas)


