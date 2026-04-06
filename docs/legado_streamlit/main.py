# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. session_state_defaults → Inicializa variáveis de sessão
# 2. layout                → Carrega dados e renderiza dashboard
# 3. main flow             → Login → Menu → Layout
# -------------------------------------------------------------------

import streamlit as st
from dotenv import load_dotenv
from libs.views.componentes import menu_principal, login_ui, apply_custom_css
from libs.controllers.data_controller import carregar_dados
from libs.controllers.config_controller import load_app_config
from libs.views.pages import render_main_dashboard

# -------------------------------------------------------------------
# CONFIGURAÇÕES
# -------------------------------------------------------------------
deploy = True

DEFAULTS = {
    "logado": False,
    "load_data": None,
    "usina": None,
    "list_cards": None,
    "grafico_energia": None,
    "grafico_nivel": None,
    "periodo": None,
    "data_inicial": None,
    "data_final": None,
    "ultima_atualizacao": None,
}

# -------------------------------------------------------------------
# FUNÇÕES
# -------------------------------------------------------------------
def _init_session_defaults():
    for key, default in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default


def layout():
    tem_filtro = all([
        st.session_state["periodo"],
        st.session_state["data_inicial"],
        st.session_state["data_final"],
        st.session_state["load_data"],
    ])

    if tem_filtro:
        carregar_dados(
            periodo=st.session_state.periodo,
            data_inicial=st.session_state.data_inicial,
            data_final=st.session_state.data_final,
        )
        st.session_state["load_data"] = False

    if st.session_state["load_data"] is None:
        carregar_dados(periodo=None, data_inicial=None, data_final=None)
        st.session_state["load_data"] = False

    render_main_dashboard()


# -------------------------------------------------------------------
# EXECUÇÃO
# -------------------------------------------------------------------
_init_session_defaults()

st.set_page_config(
    page_title="EngeGOM",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_custom_css()
load_dotenv()

config = load_app_config(deploy)
st.session_state["usinas"] = config["usinas"]

if not st.session_state["logado"]:
    login_ui()
    st.stop()

menu_principal(config, st.session_state["usina"])
layout()
