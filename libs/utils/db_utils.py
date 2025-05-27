from libs.models.db import Database
import streamlit as st

def init_db_connection():
    """
    Inicializa a conexão com o banco de dados no session_state, se ainda não existir ou estiver None.
    """
    if 'db' not in st.session_state or st.session_state['db'] is None:
        try:
            st.session_state['db'] = Database()
        except Exception as e:
            print(f"Erro ao inicializar conexão com o banco: {e}")
            st.session_state['db'] = None 