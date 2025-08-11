# Conteúdo inicial
import streamlit as st
from datetime import datetime, timedelta
from libs.utils.decorators import desempenho, get_error
from libs.models.datas import get_data_card_energia, get_grafico_energia, get_grafico_nivel, get_names_all_columns


@desempenho
def carregar_dados(periodo, data_inicial, data_final):
    try:
        if st.session_state.get('list_cards') is None:
            st.session_state.list_cards = get_data_card_energia()
        
        if periodo == 'M':
            data_inicial = data_inicial - timedelta(days=30)
        st.write('st.session_state.list_cards: ',st.session_state.list_cards)
        # st.session_state.grafico_energia = get_grafico_energia(periodo, data_inicial, data_final)
        # st.session_state.grafico_nivel = get_grafico_nivel(periodo)
        # st.session_state.columns_names = get_names_all_columns()
    except Exception as e:
        get_error('carregar_dados, ln 313', e) # The line number here will be incorrect after moving

@desempenho
def set_load_data():
    st.session_state.load_data = False
