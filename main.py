import streamlit as st
# import yaml # No longer used directly
from dotenv import load_dotenv
# import pandas as pd # No longer used directly
from libs.views.componentes import menu_principal, login_ui, apply_custom_css # Adjusted imports
# import os # No longer used directly
from libs.utils.decorators import desempenho # get_error is no longer used directly here
from datetime import datetime, timedelta # Still used for default dates in layout
from libs.controllers.auth import logout
from libs.controllers.data_controller import carregar_dados, set_load_data # set_load_data might not be explicitly called
from libs.controllers.config_controller import load_app_config
from libs.views.pages import render_main_dashboard # Added import
from libs.models.datas import get_periodo, get_ultimos_1_hora_nivel # Added for data loading logic in layout
from libs.utils.db_utils import init_db_connection  # Adicionado para garantir inicialização do db

deploy = True

if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'load_data' not in st.session_state: # This flag is managed by the layout function
    st.session_state['load_data'] = False
if 'usina' not in st.session_state:
    st.session_state['usina'] = None
# Initialize session state for data if not present, to avoid errors in render_main_dashboard if layout isn't called first
if 'list_cards' not in st.session_state:
    st.session_state.list_cards = None
if 'ultimos_30_dias' not in st.session_state:
    st.session_state.ultimos_30_dias = None
if 'ultimos_1_hora_nivel' not in st.session_state:
    st.session_state.ultimos_1_hora_nivel = None
if "db" not in st.session_state:
    st.session_state["db"] = None  # ou algum valor padrão apropriado

# Inicializa a conexão com o banco de dados
init_db_connection()

st.set_page_config(
    page_title="EngeGOM",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_custom_css() # Moved CSS application here

load_dotenv() 

config = load_app_config(deploy) 
st.session_state['usinas'] = config['usinas']

# @desempenho # Decorator removed as per instruction
def layout(usina): # `usina` is the selected usina config dict
    # Data loading orchestration
    if not st.session_state.load_data:
        if 'periodo' in st.session_state and 'data_inicial' in st.session_state and 'data_final' in st.session_state:
            # This part implies that period, data_inicial, data_final are set by another component (e.g., create_grafico_producao_energia's date pickers)
            # And that st.session_state.load_data = False was triggered by that component.
            st.session_state.ultimos_30_dias = get_periodo(st.session_state.periodo, st.session_state.data_inicial, st.session_state.data_final)
            # Assuming get_ultimos_1_hora_nivel also needs to be reloaded if date_inicial/final change
            st.session_state.ultimos_1_hora_nivel = get_ultimos_1_hora_nivel(st.session_state.data_inicial, st.session_state.data_final)
            # list_cards might not be reloaded here, depends on desired behavior.
            # If list_cards depends on the date range, it should be reloaded.
            # For now, assuming carregar_dados (which loads list_cards) is for initial load or full refresh.
        else:
            # Default data loading when page is first loaded or no specific period is set by user interaction
            default_data_inicial = datetime.now() - timedelta(days=30)
            default_data_final = datetime.now()
            # carregar_dados loads list_cards, ultimos_30_dias (default 30 days, M), and ultimos_1_hora_nivel
            carregar_dados(usina, periodo='M', data_inicial=default_data_inicial, data_final=default_data_final) 
        st.session_state.load_data = True # Mark data as loaded

    # Call the rendering function from pages.py with data from session_state
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
    menu_principal(config, st.session_state['usina']) 
    layout(st.session_state['usina'])
