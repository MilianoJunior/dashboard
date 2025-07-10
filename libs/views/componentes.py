import base64
import re
from typing import Dict
from datetime import datetime, timedelta
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import plotly.express as px
from libs.controllers.auth import authenticate_user # ADDED
import streamlit.components.v1 as components
import streamlit as st # Certifique-se que está importado
# from libs.views.pages import render_main_dashboard
from libs.models.calculos import calcular_energia_acumulada
import random
from libs.utils.decorators import desempenho
# import streamlit as st
# import pandas as pd
import io
# from datetime import datetime


@desempenho
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
            div[data-testid="stForm"] {background:#161a1d;border:1px solid #30363d;
                           border-radius:10px;padding:1rem;margin-bottom:1rem;}
            .stButton>button {background:#06a0e3;color:#fff;border:0;border-radius:6px;
                            font-weight:600;padding:0.5rem 1.25rem;cursor:pointer;}
            .stButton>button:hover {filter:brightness(1.1);}
        </style>
    """, unsafe_allow_html=True)

@desempenho
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


@desempenho
def create_energy_card(description, value, data_hora, medida, percentual, value_max=None, value_min=None, valor_real=None, valor_Mwh=None, percentual_participacao=None, valor_ano_anterior=None):
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

    if valor_ano_anterior is not None:
        valor_ano_anterior = f"R$ {valor_ano_anterior:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".")
    else:
        valor_ano_anterior = ""

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
                <div class="maxmin">Per.: {valor_percentual}</div>
            </div>
        </div>
    """
    return st.markdown(card_style + card_html, unsafe_allow_html=True)


@desempenho
def carregar_logo(usina):
    with open(f'assets/logo.png', 'rb') as file:
        logo_bytes = file.read()
        return logo_bytes

@desempenho
def menu_principal(config, usina):
    import base64
    logo_bytes = carregar_logo(usina)
    logo_html = f'<img src="data:image/png;base64,{base64.b64encode(logo_bytes).decode()}" alt="Logo" style="height:60px;border-radius:50px;background:#fff;padding:2px;">'

    col1, col2 = st.columns([8, 1])
    # print('usina: ',usina)
    # print('-' * 50)
    # print('config: ',config)
    with col1:
        st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 10px; background-color: #2c2c2c; border-radius: 15px; padding: 7px; margin: 2px;">
                {logo_html}
                <span style="font-family: 'Inter', system-ui, Arial, sans-serif; font-size: 24px; font-weight: 400; color: white;">
                    Dashboard {usina['users'].upper()}
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

@desempenho
def rename_colunas(df: pd.DataFrame) -> pd.DataFrame:
    def formata_nome(col: str) -> str | None:
        m = re.search(r'ug[_\-]?(\d{2})', col.lower())
        if m:
            num = m.group(1)
            return f'UG-{num} (MWh)'
        return None

    mapeamento = {
        col: novo 
        for col in df.columns
        if (novo := formata_nome(col)) is not None
    }

    return df.rename(columns=mapeamento)

def formulario_filtro_producao():
        # ---------- FORMULÁRIO DE FILTRO (inputs + botão) ----------
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1], gap="small", vertical_alignment="bottom", border=False)

    with c1:
        opções = {"Hora": "H", "Diário": "D", "Mensal": "M"}
        escolha = st.segmented_control("", list(opções.keys()), default="Diário")
        periodo = opções[escolha]

    hoje = datetime.now()
    if periodo in ("D", "M"):
        with c2:
            delta = 30 if periodo == "D" else 365
            # Crie as subcolunas para datas fora de qualquer bloco de coluna
            inicio = st.date_input("Data inicial", hoje - timedelta(days=delta), key="dt_ini")
        with c3:
            fim = st.date_input("Data final", hoje, key="dt_fim")
    else:
        with c2:
            ontem = hoje - timedelta(days=1)
            dia = st.date_input("Data (HH:00-23:59)", ontem, key="dt_unica")
            inicio = datetime.combine(dia, datetime.min.time())
            fim = inicio + timedelta(hours=23, minutes=59, seconds=59)
        with c3:
            pass

    with c4:
        atualizar = st.button("Atualizar")

    if atualizar:
        st.session_state.update(
            data_inicial=inicio,
            data_final=fim,
            periodo=periodo,
            load_data=True,
        )
        st.rerun()  # força recarga após setar estado

# ---------- função de exibição -------------------------------------------
def create_grafico_producao_energia():

    st.divider()

    formulario_filtro_producao()

    df = st.session_state['grafico_energia']
    if df.empty:
        st.info('Não há dados para exibir para este período.')
        return

    df = rename_colunas(df)                     # sua função
    col_prod = [c for c in df.columns if c.endswith('(MWh)')]
    df['Total'] = df[col_prod].sum(axis=1)

    # ---------- GRÁFICO ----------------------------------------------------
    fig = px.bar(
        df, x=df.index, y='Total', title='Geração de Energia',
        height=500, color_discrete_sequence=['#6EC1E4']
    )

    # anotações (mesma lógica) ---------------------------------------------
    for idx, row in df.iterrows():
        linha = "<br>".join(f"{c.split()[0]}: {row[c]:.1f}" for c in col_prod)
        if len(col_prod) > 1:
            linha += f"<br><b>Total: {row['Total']:.1f}</b>"
        fig.add_annotation(
            x=idx, y=row['Total'] * 1.10, text=linha, showarrow=False,
            font=dict(size=10), bgcolor="rgba(0,0,0,0.8)",
            bordercolor='rgba(255,255,255,0.3)', borderwidth=1, borderpad=4
        )

    fig.update_traces(marker_line_width=1.5, marker_line_color='rgba(30,30,30,0.25)')
    fig.update_layout(
        title=dict(x=0.02, xanchor='left'), margin=dict(l=10, r=10, t=40, b=10),
        yaxis_title='Energia (MWh)', xaxis_title='', showlegend=False,
        xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.15)'),
        yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.15)')
    )

    st.plotly_chart(fig, use_container_width=True)


def card_download_dados():
    df = st.session_state.get("dados")
    if df is None or df.empty:
        st.info("Não há dados carregados para download.")
        return

    st.markdown("### 📥 Exportar dados")
    col_csv, col_xlsx = st.columns(2, gap="small")

    # ---------- CSV -------------------------------------------------------
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    with col_csv:
        st.download_button(
            "⬇️ Baixar CSV",
            csv_bytes,
            file_name=f"dados_{datetime.now():%Y%m%d_%H%M%S}.csv",
            mime="text/csv",
            key="download-csv",
        )

    # ---------- XLSX (com fallback) ---------------------------------------
    try:
        buffer = io.BytesIO()
        # tente XlsxWriter; se não houver, caia para openpyxl
        try:
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="dados")
        except ImportError:
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="dados")
        buffer.seek(0)

        with col_xlsx:
            st.download_button(
                "⬇️ Baixar Excel",
                buffer.getvalue(),
                file_name=f"dados_{datetime.now():%Y%m%d_%H%M%S}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download-xlsx",
            )
    except ImportError:
        st.warning(
            "A exportação para Excel requer os pacotes **XlsxWriter** ou **openpyxl**. "
            "Adicione um deles ao seu ambiente para habilitar esse download."
        )

# ----------------------------------------------------------------------------
# def card_download_dados():
#     """Renderiza um 'cartão' de exportação para CSV / Excel."""
#     df = st.session_state.get("dados")

#     if df is None or df.empty:
#         st.info("Não há dados carregados para download.")
#         return

#     # --- Cabeçalho visual ---------------------------------------------------
#     st.markdown("### 📥 Exportar dados")

#     # Layout 2 colunas – um botão para cada formato
#     col_csv, col_xlsx = st.columns(2, gap="small")

#     # --------- CSV ---------------------------------------------------------
#     with col_csv:
#         csv_bytes = df.to_csv(index=False).encode("utf-8")
#         st.download_button(
#             label="⬇️ Baixar CSV",
#             data=csv_bytes,
#             file_name=f"dados_{datetime.now():%Y%m%d_%H%M%S}.csv",
#             mime="text/csv",
#             key="download-csv",
#         )

#     # --------- Excel -------------------------------------------------------
#     with col_xlsx:
#         buffer = io.BytesIO()
#         with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
#             df.to_excel(writer, index=False, sheet_name="dados")
#         buffer.seek(0)

#         st.download_button(
#             label="⬇️ Baixar Excel",
#             data=buffer.getvalue(),
#             file_name=f"dados_{datetime.now():%Y%m%d_%H%M%S}.xlsx",
#             mime=(
#                 "application/vnd.openxmlformats-officedocument."
#                 "spreadsheetml.sheet"
#             ),
#             key="download-xlsx",
#         )



# @desempenho
# def create_grafico_producao_energia():
#     df = st.session_state['grafico_energia']
#     # st.write('df antes: ',df)
#     if df.empty:
#         st.write('Não há dados para exibir para este período')
#         return
#     df = rename_colunas(df)
#     # st.write('df: ',df)
#     # print('df.columns: ',df.columns)
#     # print('df.shape: ',df.shape)
#     st.divider()
#     # st.write('df: ',df)

#     # # Identifica as colunas de produção (todas renomeadas para 'UG-XX (MWh)')
#     colunas_prod = [c for c in df.columns if c.endswith('(MWh)')]

#     # # Total diário
#     df['Total'] = df[colunas_prod].sum(axis=1)
#     # Gráfico de barras
#     fig = px.bar(
#         df,
#         x=df.index,
#         y='Total',
#         title='Geração de Energia',
#         height=500,
#         color_discrete_sequence=['#6EC1E4']
#     )

#     # # Anotações detalhadas
#     for idx, row in df.iterrows():
#         valores = [f"{col.split()[0]}: {row[col]:.1f}" for col in colunas_prod]
#         texto = "<br>".join(valores)
#         if len(colunas_prod) > 1:
#             texto += f"<br><b>Total: {row['Total']:.1f}</b>"
#         fig.add_annotation(
#             x=idx, y=row['Total'] * 1.15,
#             text=texto, showarrow=False,
#             font=dict(color='white', size=10),
#             bgcolor="rgba(0,0,0,0.8)",
#             bordercolor='rgba(255,255,255,0.3)',
#             borderwidth=1, borderpad=4
#         )

#     fig.update_traces(marker=dict(line=dict(width=2, color='rgba(30,30,30,0.18)')))
#     fig.update_layout(
#         title=dict(text='Geração de Energia', x=0.01, xanchor='left'),
#         yaxis_title='Energia (MWh)', xaxis_title='',
#         showlegend=False, margin=dict(l=10, r=10, t=10, b=10),
#         xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
#         yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)')
#     )

#     # # Exibe tabela e controles de período
#     with st.container():
#         # st.write(df)
#         cols_btns = st.columns([1, 1, 1])

#         with cols_btns[0]:
#             # Seleção de período
#             opções = {"Hora": "H", "Diário": "D", "Mensal": "M"}
#             escolha = st.segmented_control("", list(opções.keys()), default="Diário")
#             periodo = opções[escolha]

#         with cols_btns[1]:
#             # Inputs de data
#             hoje = datetime.now()
#             if periodo == "D" or periodo == "M":
#                 delta = 30 if periodo == "D" else 365
#                 inicio = st.date_input("Data inicial", hoje - timedelta(days=delta))
#                 fim = st.date_input("Data final", hoje)
#             else:
#                 hoje = datetime.now() - timedelta(days=1)
#                 dia = st.date_input("Data", hoje)
#                 inicio = datetime.combine(dia, datetime.min.time())
#                 fim = inicio + timedelta(hours=23, minutes=59, seconds=59)

#         with cols_btns[2]:
#             if st.button("Atualizar"):
#                 print('Atualizando dados...')
#                 st.session_state['data_inicial'] = inicio
#                 st.session_state['data_final'] = fim
#                 st.session_state['periodo'] = periodo
#                 st.session_state['load_data'] = True
#                 st.rerun()

#     st.plotly_chart(fig, use_container_width=True)

@desempenho
def create_grafico_nivel():

    df = st.session_state['grafico_nivel']
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
        # print(f'col: {col}')
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
            xanchor='right',
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

@desempenho
def login_ui():
    st.image('assets/login.png', width=300)
    usinas = list(st.session_state['usinas'].keys())
    usina_nome = st.selectbox('Selecione a usina', usinas)
    usuario = st.text_input('Usuário', value='admin', label_visibility="collapsed")
    senha = st.text_input('Senha', type='password', value='admin')
    
    if st.button('Entrar'):
        autenticado, usina_obj = authenticate_user(usuario, senha, usina_nome, st.session_state['usinas'])
        
        if autenticado:
            st.session_state['logado'] = True
            st.session_state['usina'] = usina_obj
            st.success('Login realizado com sucesso!')
            st.rerun()
        else:
            st.error('Usuário ou senha inválidos para esta usina.')

@desempenho
def footer(usina):
    st.divider()
    st.write(f'Usina: {usina}')
    st.write('EngeSEP - Engenharia integrada de sistemas')
