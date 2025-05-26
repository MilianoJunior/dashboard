# Conteúdo inicial
import streamlit as st
from libs.views.componentes import create_energy_card, create_grafico_producao_energia, create_grafico_nivel, footer
# Removed: from libs.models.datas import get_data_card_energia, get_ultimos_30_dias, get_ultimos_1_hora_nivel (these are handled in main.py)
# Removed: from libs.utils.decorators import desempenho, get_error (decorators are not used here directly for now)
# Removed: from datetime import datetime, timedelta (not directly used in this UI rendering function)

def render_main_dashboard(usina_selecionada, list_cards_data, ultimos_30_dias_data, ultimos_1_hora_nivel_data):
    col1, col2 = st.columns([1, 5])
    
    with col1:
        st.divider()
        st.markdown('##### Calculadora de receita')
        col2_1, col2_2 = st.columns([1, 1])
        with col2_1:
            valor_Mwh = st.number_input('Valor do MWh R$', value=450.00, format='%0.2f')
        with col2_2:
            percentual_participacao = st.number_input('Participação %', value=100.00,  min_value=0.00, max_value=100.00, format='%0.2f')
        
        # Use the passed data argument 'list_cards_data'
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
                                   percentual_participacao=percentual_participacao)
        else:
            st.write("Dados dos cards de energia não disponíveis.") # Placeholder if data is None

    with col2:
        # Use the passed data arguments
        if ultimos_30_dias_data is not None:
             create_grafico_producao_energia(ultimos_30_dias_data)
        else:
            st.write("Dados para o gráfico de produção de energia não disponíveis.") # Placeholder
        
        if ultimos_1_hora_nivel_data is not None:
            create_grafico_nivel(ultimos_1_hora_nivel_data)
        else:
            st.write("Dados para o gráfico de nível não disponíveis.") # Placeholder

    # Use the passed usina_selecionada argument
    if usina_selecionada and "tabela" in usina_selecionada:
        footer(usina_selecionada["tabela"].replace("_", " ").capitalize())
    else:
        footer("Usina não especificada") # Placeholder
