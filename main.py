import streamlit as st
import yaml
from dotenv import load_dotenv
import pandas as pd
from libs.componentes import (create_energy_card, 
                              menu_principal, 
                              create_grafico_producao_energia, 
                              create_grafico_nivel,
                              login_ui,
                              footer)
import os
from libs.utils.decorators import desempenho, get_error
# from libs.models.db import Database
from datetime import datetime, timedelta

deploy = True

if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'load_data' not in st.session_state:
    st.session_state['load_data'] = False
if 'usina' not in st.session_state:
    st.session_state['usina'] = None

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

st.session_state['usinas'] = config['usinas']

def logout():
    st.session_state.clear()
    st.rerun()

@desempenho
def carregar_dados(usina, periodo='M', data_inicial=datetime.now() - timedelta(days=30), data_final=datetime.now()):
    from libs.models.datas import get_data_card_energia, get_ultimos_30_dias, get_ultimos_1_hora_nivel, get_names_all_columns, get_periodo
    try:
        if periodo == 'Mensal':
            periodo = 'M'
        else:
            periodo = 'D'
        st.session_state.list_cards = get_data_card_energia()
        st.session_state.ultimos_30_dias = get_ultimos_30_dias(periodo, 30)
        st.session_state.ultimos_1_hora_nivel = get_ultimos_1_hora_nivel(data_inicial, data_final)
        # st.session_state.names_all_columns = get_names_all_columns()
        # st.session_state.temperatura = get_temperatura()
    except Exception as e:
        get_error('carregar_dados, ln 313', e)

@desempenho
def set_load_data():
    st.session_state.load_data = False

@desempenho
def layout(usina):
    if not st.session_state.load_data:
        if 'periodo' in st.session_state:
            from libs.models.datas import  get_periodo, get_ultimos_1_hora_nivel
            st.session_state.ultimos_30_dias = get_periodo(st.session_state.periodo, st.session_state.data_inicial, st.session_state.data_final)
            st.session_state.ultimos_1_hora_nivel = get_ultimos_1_hora_nivel(st.session_state.data_inicial, st.session_state.data_final)
        else:
            carregar_dados(usina)
        st.session_state.load_data = True
    col1, col2 = st.columns([5, 1])
    with col1:
        create_grafico_producao_energia(st.session_state.ultimos_30_dias)
        # st.divider()
        create_grafico_nivel(st.session_state.ultimos_1_hora_nivel)
    with col2:
        st.divider()
        col2_1, col2_2 = st.columns([1, 1])
        
        with col2_1:
            valor_Mwh = st.number_input('Valor do MWh R$', value=450.00, format='%0.2f')
        with col2_2:
            percentual_participacao = st.number_input('Participação %', value=100.00,  min_value=0.00, max_value=100.00, format='%0.2f')
        for i, (key, value) in enumerate(st.session_state.list_cards.items()):
            create_energy_card(description=key, 
                               value=value['value'], 
                               data_hora=value['data_hora'], 
                               medida=value['medida'], 
                               percentual=value['percentual'], 
                               value_max=value['value_max'], 
                               value_min=value['value_min'], 
                               valor_real=value['valor_real'],
                               valor_Mwh=valor_Mwh,
                               percentual_participacao=percentual_participacao)
    footer(usina["tabela"].replace("_", " ").capitalize())


if not st.session_state['logado']:
    login_ui()
    st.stop()

if st.session_state['logado']:
    menu_principal(config, st.session_state['usina'])
    layout(st.session_state['usina'])
# 281 linhas - 160 linhas
