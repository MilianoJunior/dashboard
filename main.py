import streamlit as st
from dotenv import load_dotenv
from libs.views.componentes import menu_principal, login_ui, apply_custom_css
# from libs.utils.decorators import desempenho # REMOVED as it's no longer used in main.py
from datetime import datetime, timedelta 
from libs.controllers.auth import logout
from libs.controllers.data_controller import carregar_dados, set_load_data 
from libs.controllers.config_controller import load_app_config
from libs.views.pages import render_main_dashboard # Added import
from libs.models.datas import get_periodo, get_ultimos_1_hora_nivel # Added for data loading logic in layout
from libs.utils.db_utils import init_db_connection  # Adicionado para garantir inicialização do db

deploy = True

if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'load_data' not in st.session_state: 
    st.session_state['load_data'] = False
if 'usina' not in st.session_state:
    st.session_state['usina'] = None
if 'list_cards' not in st.session_state:
    st.session_state.list_cards = None
if 'ultimos_30_dias' not in st.session_state:
    st.session_state.ultimos_30_dias = None
if 'ultimos_1_hora_nivel' not in st.session_state:
    st.session_state.ultimos_1_hora_nivel = None

# Inicializa a conexão com o banco de dados
init_db_connection()

st.set_page_config(
    page_title="EngeGOM",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_custom_css() 

load_dotenv() 

config = load_app_config(deploy) 
st.session_state['usinas'] = config['usinas']

def layout(usina): 
    if not st.session_state.load_data:
        if 'periodo' in st.session_state and 'data_inicial' in st.session_state and 'data_final' in st.session_state:
            st.session_state.ultimos_30_dias = get_periodo(st.session_state.periodo, st.session_state.data_inicial, st.session_state.data_final)
            st.session_state.ultimos_1_hora_nivel = get_ultimos_1_hora_nivel(st.session_state.data_inicial, st.session_state.data_final)
        else:
            default_data_inicial = datetime.now() - timedelta(days=30)
            default_data_final = datetime.now()
            carregar_dados(usina, periodo='M', data_inicial=default_data_inicial, data_final=default_data_final) 
        st.session_state.load_data = True 

    render_main_dashboard(
        usina_selecionada=usina, 
        list_cards_data=st.session_state.get('list_cards'), 
        ultimos_30_dias_data=st.session_state.get('ultimos_30_dias'), 
        ultimos_1_hora_nivel_data=st.session_state.get('ultimos_1_hora_nivel')
    )

if not st.session_state['logado']:
    login_ui()
    st.stop()

if st.session_state['logado']:
    # Manage Database instance in session_state
    if 'db' not in st.session_state or st.session_state.get('db') is None: 
        logger.info("Inicializando instância Database em st.session_state['db']")
        st.session_state['db'] = Database()
    # else: # Optional: log if it already existed
        # logger.debug("Instância Database já existe em st.session_state['db']")
    print('Executando passo 1')
    menu_principal(config, st.session_state['usina']) 
    layout(st.session_state['usina'])