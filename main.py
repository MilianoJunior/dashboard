import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from libs.views.componentes import menu_principal, login_ui, apply_custom_css
import time
from datetime import datetime, timedelta 
from libs.controllers.data_controller import carregar_dados
from libs.controllers.config_controller import load_app_config
from libs.views.pages import render_main_dashboard
# from libs.models.datas import get_periodo, get_ultimos_1_hora_nivel, get_data_inicial
# from libs.models.datas import get_data_inicial
from libs.utils.db_utils import init_db_connection 

deploy = True

if 'contador' not in st.session_state:
    st.session_state.contador = 0

if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'load_data' not in st.session_state: 
    st.session_state['load_data'] = None
if 'usina' not in st.session_state:
    st.session_state['usina'] = None
if 'list_cards' not in st.session_state:
    st.session_state.list_cards = None
if 'grafico_energia' not in st.session_state:
    st.session_state.grafico_energia = None
if 'grafico_nivel' not in st.session_state:
    st.session_state.grafico_nivel = None
if 'periodo' not in st.session_state:
    st.session_state.periodo = None
if 'data_inicial' not in st.session_state:
    st.session_state.data_inicial = None
if 'data_final' not in st.session_state:
    st.session_state.data_final = None
if 'ultima_atualizacao' not in st.session_state:
    st.session_state.ultima_atualizacao = None



print(' ' *10)
print(' ' *10)
print(' ' *10)
print(' ' *10)
print('###' *10)
print('  1 - função principal: init_db_connection')
inicio = time.time()
# # Inicializa a conexão com o banco de dados
init_db_connection(st)
fim = time.time()
print(f'tempo: {fim - inicio:.4f} s')
print('###' *10)

print('  2 - função principal: set_page_config')
inicio = time.time()
st.set_page_config(
    page_title="EngeGOM",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)
fim = time.time()
print(f'tempo: {fim - inicio:.4f} s')
print('###' *10)


print('  3 - função principal: apply_custom_css')
inicio = time.time()
apply_custom_css() 
print(f'tempo: {fim - inicio:.4f} s')
print('###' *10)

load_dotenv() 

print('  4 - função principal: load_app_config')
inicio = time.time()
config = load_app_config(deploy)
st.session_state['usinas'] = config['usinas']
print(f'tempo: {fim - inicio:.4f} s')
print('###' *10)



def layout(): 
    if st.session_state['periodo'] is not None and st.session_state['data_inicial'] is not None and st.session_state['data_final'] is not None and st.session_state['load_data']:
        print('  9 - função principal: carregar_dados, periodo: ',st.session_state.periodo, 'data_inicial: ',st.session_state.data_inicial, 'data_final: ',st.session_state.data_final)
        carregar_dados(periodo=st.session_state.periodo, data_inicial=st.session_state.data_inicial, data_final=st.session_state.data_final)
        st.session_state['load_data'] = False
    if st.session_state['load_data'] is None:
        print('  9 - função principal: carregar_dados, periodo: None, data_inicial: None, data_final: None')
        carregar_dados(periodo=None, data_inicial=None, data_final=None) 
        st.session_state['load_data'] = False
    render_main_dashboard()

inicio = time.time()
if not st.session_state['logado']:
    print('  5 - função principal: login_ui')
    login_ui()
    fim = time.time()
    print(f'tempo: {fim - inicio:.4f} s')
    print('###' *10)
    st.stop()


if st.session_state['logado']:
    print('  7 - função principal: menu_principal')
    inicio = time.time()
    menu_principal(config, st.session_state['usina'])
    # st.write(st.session_state['dados'])
    fim = time.time()
    print(f'tempo: {fim - inicio:.4f} s')
    print('###' *10)
    print('  8 - função principal: layout')
    inicio = time.time()
    layout()
    fim = time.time()
    print(f'tempo: {fim - inicio:.4f} s')
    print('###' *10)
    
