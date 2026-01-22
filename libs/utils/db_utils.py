from libs.models.db import Database
# import streamlit as st
from libs.utils.decorators import desempenho

@desempenho
def init_db_connection(st):
    """
    Inicializa a conexão com o banco de dados no session_state, se ainda não existir ou estiver None.
    """
    if 'db' not in st.session_state or st.session_state['db'] is None:
        try:
            st.session_state['db'] = Database()
            # st.session_state['db'].connect()
            # print('conectado ao banco de dados')
        except Exception as e:
            print(f"Erro ao inicializar conexão com o banco: {e}")
            st.session_state['db'] = None 