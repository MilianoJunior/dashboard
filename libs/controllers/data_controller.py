# Conteúdo inicial
import streamlit as st
from datetime import datetime, timedelta
from libs.utils.decorators import desempenho, get_error
from libs.models.datas import get_data_card_energia, get_ultimos_30_dias, get_ultimos_1_hora_nivel, get_periodo # get_names_all_columns removed

@desempenho
def carregar_dados(usina, periodo='M', data_inicial=datetime.now() - timedelta(days=30), data_final=datetime.now()):
    # Removed: from libs.models.datas import get_data_card_energia, get_ultimos_30_dias, get_ultimos_1_hora_nivel, get_names_all_columns, get_periodo
    # Imports are now at the top of the file
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
        get_error('carregar_dados, ln 313', e) # The line number here will be incorrect after moving

@desempenho
def set_load_data():
    st.session_state.load_data = False
