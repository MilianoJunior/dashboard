# Conteúdo inicial
import streamlit as st
from libs.views.componentes import create_energy_card, create_grafico_producao_energia, create_grafico_nivel, footer, card_download_dados
from libs.utils.decorators import desempenho
# Removed: from libs.models.datas import get_data_card_energia, get_ultimos_30_dias, get_ultimos_1_hora_nivel (these are handled in main.py)
# Removed: from libs.utils.decorators import desempenho, get_error (decorators are not used here directly for now)
# Removed: from datetime import datetime, timedelta (not directly used in this UI rendering function)

@desempenho
def render_main_dashboard():
    col1, col2 = st.columns([1, 5])
    with col1:
        st.divider()
        st.markdown('##### Calculadora de receita')
        col2_1, col2_2 = st.columns([1, 1])
        with col2_1:
            valor_Mwh = st.number_input('Valor do MWh R$', value=450.00, format='%0.2f')
        with col2_2:
            percentual_participacao = st.number_input('Participação %', value=100.00,  min_value=0.00, max_value=100.00, format='%0.2f')
        
        list_cards_data = st.session_state.get('list_cards')
        if list_cards_data:
            for i, (key, value) in enumerate(list_cards_data.items()):
                create_energy_card(description=key, 
                                   value=value['value'], 
                                   data_hora=value['data_hora'], 
                                   medida=value['medida'], 
                                   percentual=value['percentual'], 
                                   value_max=value['value_max'], 
                                   value_min=value['value_min'], 
                                   valor_real=value['valor_real'],
                                   valor_Mwh=valor_Mwh,
                                   percentual_participacao=percentual_participacao,
                                   valor_ano_anterior=value['ano_anterior'])
        else:
            st.write("Dados dos cards de energia não disponíveis.") # Placeholder if data is None

    with col2:
        # st.write('col2')
        # Use the passed data arguments
        if st.session_state['grafico_energia'] is not None:
             create_grafico_producao_energia()
        else:
            st.write("Dados para o gráfico de produção de energia não disponíveis.") # Placeholder
        
        if st.session_state.get('grafico_nivel') is not None:
            create_grafico_nivel()
        else:
            st.write("Dados para o gráfico de nível não disponíveis.") # Placeholder

        card_download_dados()

    # Use the passed usina_selecionada argument
    if st.session_state['usina'] and "users" in st.session_state['usina']:
        footer(st.session_state['usina']['users'])
    else:
        footer("Usina não especificada") # Placeholder
        
