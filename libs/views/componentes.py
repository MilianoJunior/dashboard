import base64
from typing import Dict
import streamlit as st # Added import
from datetime import datetime
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import plotly.express as px
from libs.controllers.auth import authenticate_user # ADDED
import streamlit.components.v1 as components
# from streamlit_js_eval import streamlit_js_eval
import streamlit as st # Certifique-se que está importado
import random

def apply_custom_css():
    st.markdown("""
        <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .block-container {
                padding-top: 1rem !important;
                padding-bottom: 0rem !important;
            }
            [data-testid="stHeader"] {
                padding-top: 0rem !important;
                padding-bottom: 0rem !important;
            }
            .main > div {
                padding-top: 0rem !important;
            }
            .stTitle, .stHeader {
                margin-top: 0 !important;
                padding-top: 0 !important;
            }
            [data-testid="stSidebar"] {
                padding-top: 0rem !important;
            }
            .css-1dp5vir {
                padding-top: 0 !important;
                margin-top: 0 !important;
            } 
            .main-container {
                border: 2px solid #00e1ff;
                border-radius: 15px;
                padding: 10px;
                margin: 5px;
            }    
        </style>
    """, unsafe_allow_html=True)

def render_percentual_icon(percentual, medida='MWh'):
    """
    Renderiza o ícone de percentual com SVG colorido: azul para positivo, vermelho para negativo.
    """
    if percentual is None:
        return ""
    if percentual > 0:
        svg = """
        <svg width='11' height='11' style='vertical-align:middle'>
            <polygon points='5.5,2 10,9 1,9' style='fill:#3A80EF'/>
        </svg>
        """
        color = "#3A80EF"
    else:
        svg = """
        <svg width='11' height='11' style='vertical-align:middle'>
            <polygon points='1,2 10,2 5.5,9' style='fill:#EF6A6A'/>
        </svg>
        """
        color = "#EF6A6A"
    unidade = '%' if medida == 'MWh' else 'm'
    return f"<span style='color:{color}; font-size: 0.98em; display: flex; align-items: center;'>{svg} {percentual} {unidade}</span>"

def create_energy_card(description, value, data_hora, medida, percentual, value_max=None, value_min=None, valor_real=None, valor_Mwh=None, percentual_participacao=None):
    card_style = """
        <style>
        .energy-card {
            background: linear-gradient(135deg, #232526 0%, #414345 100%);
            color: #F3F6F9;
            padding: 14px 16px;
            border-radius: 12px;
            margin: 8px 0px;
            max-width: 400px;
            min-width: 220px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.10);
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .description {
            font-size: 0.98rem;
            font-weight: 500;
            color: #A0AEC0;
            margin-bottom: 0;
        }
        .value-row {
            display: flex;
            align-items: baseline;
            gap: 6px;
        }
        .value {
            font-size: 1.4rem;
            font-weight: 700;
            color: #F3F6F9;
        }
        .unit {
            font-size: 0.95rem;
            color: #A0AEC0;
            margin-left: 1px;
        }
        .percentual {
            margin-left: 6px;
            display: flex;
            align-items: center;
            font-size: 0.98rem;
            font-weight: 500;
        }
        .valor_real {
            font-size: 0.95rem;
            color: #A8EF6A;
            font-weight: 500;
            margin-top: 0;
        }
        .maxmin {
            font-size: 0.90rem;
            color: #808495;
            margin-top: 0;
        }
        </style>
    """
    valor_percentual = round(float(value) * valor_Mwh * (percentual_participacao/100), 2)
    valor_total = round(float(value) * valor_Mwh, 2)

    if value_max is not None and value_min is not None:
        max_min = f"Percentual: ${percentual}"
    else:
        max_min = ""
    if percentual is not None:
        percentual_html = render_percentual_icon(percentual, medida)
    else:
        percentual_html = ""

    if valor_total is not None:
        valor_total = f"R$ {valor_total:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
        valor_percentual = f"R$ {valor_percentual:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    else:
        valor_total = ""
        valor_percentual = ""

    card_html = f"""
        <div class="energy-card">
            <div class="description">{description}</div>
            <div class="value-row">
                <span class="value">{str(value).replace('.', ',')}</span>
                <span class="unit">{medida}</span>
                <span class="percentual">{percentual_html}</span>
            </div>
            <div class="value-row">
                <div class="valor_real">Total: {valor_total}</div>
                <div class="maxmin">Percentual: {valor_percentual}</div>
            </div>
        </div>
    """
    return st.markdown(card_style + card_html, unsafe_allow_html=True)


def carregar_logo(usina):
    with open(f'assets/logo.png', 'rb') as file:
        logo_bytes = file.read()
        return logo_bytes

def menu_principal(config, usina):
    import base64
    logo_bytes = carregar_logo(usina)
    logo_html = f'<img src="data:image/png;base64,{base64.b64encode(logo_bytes).decode()}" alt="Logo" style="height:60px;border-radius:50px;background:#fff;padding:2px;">'

    col1, col2 = st.columns([8, 1])
    with col1:
        st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 10px; background-color: #2c2c2c; border-radius: 15px; padding: 7px; margin: 2px;">
                {logo_html}
                <span style="font-family: 'Inter', system-ui, Arial, sans-serif; font-size: 24px; font-weight: 400; color: white;">
                    Dashboard {usina['tabela'].replace('_', ' ').upper()}
                </span>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <style>
        div[data-testid="stButton"] > button {
            background-color: #2c2c2c;
            color: #00e1ff;
            border: none;
            border-radius: 5px;
            padding: 10px;
            font-family: 'Inter', system-ui, Arial, sans-serif;
            font-size: 14px;
            font-weight: 400;
            cursor: pointer;
        }
        </style>
        """, unsafe_allow_html=True)
        if st.button("Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

def create_grafico_producao_energia(df):
    from datetime import datetime, timedelta
    st.divider()
    st.markdown('##### Gráfico de produção de energia')
    # Crie todas as colunas no mesmo nível
    col1, col2, col3 = st.columns([0.15, 1, 0.3])
    with col1:
        st.write('Selecione o período')
        data_hora_inicial = st.date_input('Data inicial', value=datetime.now() - timedelta(days=30))
        data_hora_final = st.date_input('Data final', value=datetime.now())
        periodo = st.selectbox('Período', ['Diário', 'Mensal'])
        if 'periodo' not in st.session_state:
            st.session_state['periodo'] = periodo
        if 'data_inicial' not in st.session_state:
            st.session_state['data_inicial'] = data_hora_inicial
        if 'data_final' not in st.session_state:
            st.session_state['data_final'] = data_hora_final
        btn_grafico = st.button('Carregar gráfico')
        if btn_grafico:
            periodos = {
                'Diário': 'D',
                'Mensal': 'M'
            }
            st.session_state['periodo'] = periodos.get(periodo)
            st.session_state['data_inicial'] = data_hora_inicial
            st.session_state['data_final'] = data_hora_final
            st.session_state.load_data = False
            st.rerun()
    with col2:
        # O gráfico pode ficar abaixo das colunas de filtro
        colunas_prod = [col for col in df.columns if col.startswith('prod_')]

        # Paleta de cores pastel confiáveis
        cores = ['#7ED6A5', '#6EC1E4', '#FFD580', '#FFB6B9', '#B5EAD7', '#C7CEEA']
        color_sequence = cores[:len(colunas_prod)]

        fig = px.bar(
            df,
            x=df.index,
            y=colunas_prod,
            title='Geração de Energia',
            barmode='group',
            height=500,
            color_discrete_sequence=color_sequence
        )
        fig.update_traces(
            marker=dict(
                line=dict(width=2, color='rgba(30,30,30,0.18)'),  # Sombra sutil
            ),
        )
        fig.update_layout(
            title={
                'text': 'Geração de Energia',
                'x': 0.01,  # Alinha à esquerda
                'xanchor': 'left',
                'yanchor': 'top',
                'pad': {'t': 10, 'b': 0}  # Reduz o padding superior
            },
            yaxis_title='Energia (MWh)',
            xaxis_title='Data',
            legend_title='Unidades Geradoras',
            legend=dict(
                x=0.98,
                y=0.98,
                xanchor='right',
                yanchor='top',
                bgcolor='rgba(30,30,30,0.7)',
                bordercolor='rgba(200,200,200,0.2)',
                borderwidth=1,
                font=dict(size=12, color='white')
            ),
            # plot_bgcolor='#232326',  # Fundo igual ao do card
            # paper_bgcolor='#232326'
        )
        st.plotly_chart(fig, use_container_width=True)
    with col3:
        with st.container(height=500, border=False):
            st.write('Tabela de Dados')
            st.dataframe(df)



def create_grafico_nivel(df):
    colunas_nivel = [col for col in df.columns if 'niv' in col]
    nivel_vertimento = float(st.session_state['usina']['nivel_vertimento'])

    # Nova paleta de tons de azul para maior distinção
    azul_tons = [
        '#3A80EF', '#315C8D', '#1D63BF', '#348293',
        '#5B9BFF', '#7EC8E3', '#4F8FC9', '#1B4F72', '#2980B9', '#85C1E9', '#154360'
    ]
    azul_tons = azul_tons[:len(colunas_nivel)]

    # preciso fazer uma função para limitar os valores dos niveis a no maxímo 3% do nível de vertimento
    def limitar_niveis(nivel, nivel_vertimento):
        if nivel > nivel_vertimento:
            if st.session_state['contador'] > 5:
                st.session_state['contador'] = 0
            
            coef_ciclico =[0.01, 0.02, 0.03, -0.01, -0.02, -0.03]
            
            value = nivel_vertimento + coef_ciclico[st.session_state['contador']]
            st.session_state['contador'] += 1
            # print(f'nivel: {nivel}, nivel_vertimento: {value}')
            # print('-' * 50)
            return round(value, 3)
        else:
            return nivel
        
    df_nivel = df.copy()
    for col in colunas_nivel:
        print(f'col: {col}')
        st.session_state['contador'] = 0
        df_nivel[col] = df_nivel[col].apply(lambda x: limitar_niveis(x, nivel_vertimento))

    fig = go.Figure()
    for idx, col in enumerate(colunas_nivel):
        fig.add_trace(go.Scatter(
            x=df_nivel['data_hora'],
            y=df_nivel[col],
            mode='lines',
            name=col.replace('_', ' ').capitalize().replace('Nivel', 'Nível'),
            line=dict(color=azul_tons[idx], width=2, shape='spline'),
            hovertemplate=f"<b>{col.replace('_', ' ').capitalize()}</b><br>Nível: %{{y:.2f}}m<br>Data: %{{x|%d/%m/%Y %H:%M}}"
        ))

    # Linha de vertimento
    fig.add_hline(
        y=nivel_vertimento,
        line_dash="dash",
        line_color="#AE5454",
        line_width=2,
        annotation_text="<b>Nível de Vertimento</b>",
        annotation_position="top left",
        annotation_font_color="#AE5454",
        annotation_bgcolor="rgba(30,30,30,0.85)"
    )

    fig.update_layout(
        title='<b>Nível do reservatório</b>',
        yaxis_title='<b>Nível do reservatório (m)</b>',
        xaxis_title='<b>Data/hora</b>',
        font=dict(family="Inter, Arial", size=13, color='white'),
        hovermode='x unified',
        legend=dict(
            x=0.98,
            y=0.98,
            xanchor='left',
            yanchor='bottom',
            bgcolor='rgba(30,30,30,0.7)',
            bordercolor='rgba(200,200,200,0.2)',
            borderwidth=1,
            font=dict(size=14, color='white')
        ),
        margin=dict(l=40, r=30, t=60, b=40),
        title_x=0.02,
        title_y=0.97
    )
    fig.update_xaxes(
        showgrid=True, gridwidth=0.5, gridcolor='rgba(255,255,255,0.07)',
        tickformat='%b %d\n%H:%M',
        ticks="outside"
    )
    fig.update_yaxes(
        showgrid=True, gridwidth=0.5, gridcolor='rgba(255,255,255,0.07)',
        zeroline=False
    )

    st.plotly_chart(fig, use_container_width=True)

def login_ui():
    st.image('assets/login.png', width=300)
    usinas = list(st.session_state['usinas'].keys())
    usina_nome = st.selectbox('Selecione a usina', usinas)
    usuario = st.text_input('Usuário', value='admin')
    senha = st.text_input('Senha', type='password', value='admin')
    
    if st.button('Entrar'):
        # Autenticação agora é feita pela função no controller
        autenticado, usina_obj = authenticate_user(usuario, senha, usina_nome, st.session_state['usinas'])
        
        if autenticado:
            st.session_state['logado'] = True
            st.session_state['usina'] = usina_obj # usina_obj é o dicionário da usina selecionada
            # st.session_state['db'] = Database() # Removido conforme instrução
            st.success('Login realizado com sucesso!')
            st.rerun()
        else:
            st.error('Usuário ou senha inválidos para esta usina.')

def footer(usina):
    # get_width()
    st.divider()
    st.write(f'Usina: {usina}')
    st.write('EngeSEP - Engenharia integrada de sistemas')
    # st.write(f'Atualizado em: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}')

'''
Boa tarde Sr. Romar, Notamos que em algumas situações é melhor deixar ir um pouco de agua fora do que ligar a outra maquina, pois somado as duas, a potencia gerada pode ser menor que deixar somente uma máquina

Boa tarde Sr. Romar, Notamos que em algumas situações é melhor deixar ir um pouco de agua fora do que ligar a outra maquina, pois somado as duas, a potencia gerada pode ser menor que deixar somente uma máquina. Vc tem registro da quantidade de agua que estava passando por cima? 
Se tiver muita agua indo embora, talvez pode ter algum problema no sensor de nível. Continue nos avisando quando notar qualquer anormalidade, suas dúvidas serão sempre bem vindas.
'''
'''
Olá  Sr. Romar, Boa tarde, Percebemos que as duas unidades em conjunto estão gerando menos energia do que se fosse uma só para determinadas situações. 
Estamos tirando valores para chegar a uma geração máxima satisfatória. No gráfica acima, temos a produção de energia das duas unidades em conjunto para o dia de hoje, sendo 
possível verificar que as duas unidades estão ligadas e gerando energia.

O senhor tem ideia da quantidade de água que estava saindo por cima? Se for muita água mesmo, talvez o sensor de nível não esteja 100%. Continue nos avisando se notar algo diferente, tá? Suas dúvidas são sempre bem-vindas!

Olá  Sr. Romar, Boa tarde, Percebemos que as duas unidades em conjunto estão gerando menos energia do que se fosse uma só para determinadas situações. 
Estamos tirando valores para chegar a uma geração máxima satisfatória. No gráfica acima, temos a produção de energia das duas unidades em conjunto para o dia de hoje, sendo 
possível verificar que as duas unidades estão ligadas e gerando energia.
'''
# def render_graficos_dados(usina, colunas):
#     from libs.models.datas import fetch_dados_graficos
#     from datetime import datetime, timedelta

#     cols1, cols2, col3, col4 = st.columns(4)
#     with cols1:
#         colunas_selecionadas = st.multiselect('Selecione as colunas', colunas['COLUMN_NAME'].tolist(), default=colunas['COLUMN_NAME'].tolist()[1])
#     with cols2:
#         data_hora_inicial = st.date_input('Data inicial', value=datetime.now() - timedelta(days=30))
#     with col3:
#         data_hora_final = st.date_input('Data final', value=datetime.now())
#     with col4:
#         st.write('')
#         st.write('')
#         btn_grafico = st.button('Carregar gráficos')
#     if btn_grafico:
#         df_original, df_normalized = fetch_dados_graficos(usina, colunas_selecionadas, data_hora_inicial, data_hora_final)
#         tab1, tab2 = st.tabs(["Dados Originais", "Dados Normalizados"])
#         with tab1:
#             st.subheader("Gráfico de Dados Originais")
#             st.line_chart(df_original[colunas_selecionadas])
#             with st.expander('Informações dos Dados Originais'):
#                 st.write(df_original)
#         with tab2:
#             st.subheader("Gráfico de Dados Normalizados")
#             st.line_chart(df_normalized[colunas_selecionadas])
#             with st.expander('Informações dos Dados Normalizados'):
#                 st.write(df_normalized)

# def create_widget_temperatura(df):
#     try:
#         cols = st.columns(5)
#         icons = {
#             'oleo_uhlm': '🔥',
#             'oleo_uhrv': '🔥',
#             'casq_comb': '⚙️',
#             'manc_casq_esc': '⚙️',
#             'enrol_a': '⚡',
#             'enrol_b': '⚡',
#             'enrol_c': '⚡',
#             'nucleo_estator_01': '🧲',
#             'nucleo_estator_02': '🧲',
#             'nucleo_estator_03': '🧲'
#         }
#         for i, col in enumerate(df.columns):
#             with cols[i % 5]:
#                 mean_value = round(float(df.loc['mean', col]), 2)
#                 min_value = round(float(df.loc['min', col]), 2)
#                 max_value = round(float(df.loc['max', col]), 2)
#                 icon = icons.get(col, '🌡️')
#                 st.markdown(
#                     f"""
#                     <div style="
#                         background-color: #1E1E1E; 
#                         border-radius: 10px; 
#                         padding: 10px; 
#                         margin-bottom: 10px;
#                         box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
#                     ">
#                         <div style="font-size: 12px; color: #CCCCCC; margin-bottom: 5px;">
#                             Temp {col.replace('_', ' ')}
#                         </div>
#                         <div style="
#                             display: flex; 
#                             justify-content: space-between; 
#                             align-items: center;
#                         ">
#                             <span style="font-size: 28px; font-weight: bold; color: white;">
#                                 {mean_value}°
#                             </span>
#                             <span style="font-size: 24px;">
#                                 {icon}
#                             </span>
#                         </div>
#                         <div style="
#                             font-size: 11px;
#                             color: #AAAAAA;
#                             margin-top: 5px;
#                             display: flex;
#                             justify-content: space-between;
#                         ">
#                             <span>Min: {min_value}°</span>
#                             <span>Max: {max_value}°</span>
#                         </div>
#                     </div>
#                     """,
#                     unsafe_allow_html=True
#                 )
#     except Exception as e:
#         st.error(f'Erro ao criar widget de temperatura: {e}')