# Conteúdo inicial
import streamlit as st
from datetime import datetime, timedelta
from libs.utils.decorators import desempenho, get_error
from libs.models.datas import get_data_card_energia, get_grafico_energia, get_grafico_nivel, get_names_all_columns, get_db_data


@desempenho
def carregar_dados(periodo, data_inicial, data_final):
    try:
        if st.session_state.get('list_cards') is None:
            print('  10 - função principal: carregar_dados, get_data_card_energia')
            st.session_state.list_cards = get_data_card_energia()
        
        # Garantir que os dados brutos estejam carregados para download
        if st.session_state.get('dados') is None:
            print('Running manual get_db_data because dados is None')
            # Usar padrão de 30 dias se não houver dados
            di = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
            df_ = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            get_db_data(di, df_)
        
        if periodo == 'M':
            data_inicial = data_inicial - timedelta(days=30)
        # st.write('st.session_state.list_cards: ',st.session_state.list_cards)
        st.session_state.grafico_energia = get_grafico_energia(periodo, data_inicial, data_final)
        # st.write('QTD valores None: ',st.session_state.grafico_energia.isna().sum().sum())
        # st.write('st.session_state.grafico_energia: ',st.session_state.grafico_energia)
        st.session_state.grafico_nivel = get_grafico_nivel(periodo)
        # st.write('QTD valores None: ',st.session_state.grafico_nivel.isna().sum().sum())
        # st.write('st.session_state.grafico_nivel: ',st.session_state.grafico_nivel)
        st.session_state.columns_names = get_names_all_columns()
        # st.write('st.session_state.columns_names: ',st.session_state.columns_names)

    except Exception as e:
        get_error('carregar_dados, ln 313', e) # The line number here will be incorrect after moving

@desempenho
def set_load_data():
    st.session_state.load_data = False
