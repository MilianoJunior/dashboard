# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. apply_custom_css -> Carrega e aplica CSS externo
# 2. render_percentual_icon -> Helper para ícones de variação
# 3. create_energy_card -> Componente visual de cartão de energia
# 4. carregar_logo -> Lẽ logomarca e joga como bytes
# 5. menu_principal -> Cabeçalho com logo e logout
# 6. rename_colunas -> Ajusta nomes de colunas do DataFrame p/ gráficos
# 7. formulario_filtro_producao -> Renderiza botões e inputs de data/frequência
# 8. create_grafico_producao_energia -> Gráfico de barras de produção
# 9. card_download_dados -> Componente reutilizável para download dos dataframes
# 10. create_grafico_nivel -> Gráfico de linha de níveis
# 11. get_cookie_manager -> Obter cookie-manager de sessão do login
# 12. login_ui -> Interface de login
# 13. grafico_colunas_selecionadas -> Gráfico exploratório
# 14. footer -> Renderiza rodapé do dashboard
# -------------------------------------------------------------------
import base64
import re
from typing import Dict
from datetime import datetime, timedelta
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import plotly.express as px
from libs.controllers.auth import authenticate_user
import streamlit as st
from libs.controllers.data_controller import carregar_variaveis_usina, consultar_variaveis_selecionadas
from libs.utils.decorators import desempenho
import io
import extra_streamlit_components as stx

@desempenho
def apply_custom_css():
    """Lê e aplica o arquivo CSS externo."""
    try:
        with open('assets/css/custom.css', 'r') as f:
            css = f.read()
        st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.error("Arquivo CSS não encontrado em assets/css/custom.css")

@desempenho
def render_percentual_icon(percentual, medida='MWh'):
    """
    Renderiza o ícone de percentual com SVG colorido.
    """
    if percentual is None:
        return ""
    
    # Cores e ícones baseados no sinal
    if percentual > 0:
        # Triângulo para cima (Azul)
        svg = """
        <svg width='11' height='11' style='vertical-align:middle; margin-right:4px;'>
            <polygon points='5.5,2 10,9 1,9' style='fill:#3A80EF'/>
        </svg>
        """
        color = "#3A80EF"
    else:
        # Triângulo para baixo (Vermelho)
        svg = """
        <svg width='11' height='11' style='vertical-align:middle; margin-right:4px;'>
            <polygon points='1,2 10,2 5.5,9' style='fill:#EF6A6A'/>
        </svg>
        """
        color = "#EF6A6A"
    
    unidade = '%' if medida == 'MWh' else 'm'
    return f"<span style='color:{color}; display:flex; align-items:center;'>{svg}{percentual} {unidade}</span>"

@desempenho
def create_energy_card(description, value, medida, percentual, valor_mwh=None, percentual_participacao=None):
    """
    Cria um card de energia estilizado com glassmorphism.
    """
    
    # ---------------- LÓGICA DE DADOS (PRESERVADA) ----------------
    valor_percentual = 0.0
    valor_total_real = 0.0
    
    if valor_mwh and percentual_participacao:
        valor_percentual = round(float(value) * valor_mwh * (percentual_participacao / 100), 2)
        valor_total_real = round(float(value) * valor_mwh, 2)

    # Formatação de valores monetários
    def format_currency(val):
        return f"R$ {val:,.2f}".replace(",", "v").replace(".", ",").replace("v", ".") if val is not None else ""

    str_valor_total = format_currency(valor_total_real) if valor_total_real else ""
    str_valor_percentual = format_currency(valor_percentual) if valor_percentual else ""
    
    # Tratamento do HTML do percentual
    percentual_html = render_percentual_icon(percentual, medida) if percentual is not None else ""

    # Formata valor principal
    str_value = str(value).replace('.', ',')

    # ---------------- COMPOMENTE HTML ----------------
    card_html = f"""
    <div class="energy-card">
        <div class="description">{description}</div>
        <div class="value-row">
            <div class="value">{str_value}</div>
            <div class="unit">{medida}</div>
            <div class="percentual">{percentual_html}</div>
        </div>
        <div class="details-row">
            <div class="valor_real">Total: {str_valor_total}</div>
            <div class="maxmin">Parc.: {str_valor_percentual}</div>
        </div>
    </div>
    """
    
    return st.markdown(card_html, unsafe_allow_html=True)

@desempenho
def carregar_logo(usina):
    try:
        with open(f'assets/logo.png', 'rb') as file:
            return file.read()
    except Exception:
        return None

@desempenho
def menu_principal(config, usina):
    logo_bytes = carregar_logo(usina)
    
    if logo_bytes:
        b64_logo = base64.b64encode(logo_bytes).decode()
        img_tag = f'<img src="data:image/png;base64,{b64_logo}" alt="Logo" style="height:50px; border-radius:50%; background:#fff; padding:2px;">'
    else:
        img_tag = ""

    # Container do Header utilizando classes do CSS externo
    header_html = f"""
    <div class="header-container">
        {img_tag}
        <span class="header-title">
            Dashboard {usina.get('users', '').upper()}
        </span>
    </div>
    """
    
    col1, col2 = st.columns([10, 1])
    with col1:
        st.markdown(header_html, unsafe_allow_html=True)
    with col2:
        # Botão de logout estilizado via CSS global (.logout-btn-container button)
        st.markdown('<div class="logout-btn-container">', unsafe_allow_html=True)
        if st.button("Logout", key="logout_btn", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

@desempenho
def rename_colunas(df: pd.DataFrame) -> pd.DataFrame:
    def formata_nome(col: str):
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
    # Container estilizado nativo do Streamlit
    with st.container():
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1], gap="medium", vertical_alignment="bottom")

        with c1:
            opções = {"Hora": "H", "Diário": "D", "Mensal": "M"}
            escolha = st.segmented_control("Período", list(opções.keys()), default="Diário", label_visibility="visible")
            periodo = opções[escolha] if escolha else "D"

        hoje = datetime.now()
        with c2:
            if periodo in ("D", "M"):
                delta = 30 if periodo == "D" else 365
                inicio = st.date_input("Data inicial", hoje - timedelta(days=delta), key="dt_ini")
            else:
                ontem = hoje - timedelta(days=1)
                dia = st.date_input("Data", ontem, key="dt_unica")
                inicio = datetime.combine(dia, datetime.min.time())

        with c3:
            if periodo in ("D", "M"):
                fim = st.date_input("Data final", hoje, key="dt_fim")
            else:
                # Para horário H, fim é final do dia selecionado
                fim = inicio + timedelta(hours=23, minutes=59, seconds=59)

        with c4:
            atualizar = st.button("Atualizar Dados", use_container_width=True)

        if atualizar:
            st.session_state.update(
                data_inicial=inicio,
                data_final=fim,
                periodo=periodo,
                load_data=True,
            )
            st.rerun()

@desempenho
def create_grafico_producao_energia():
    st.divider()
    formulario_filtro_producao()

    df = st.session_state.get('grafico_energia', pd.DataFrame())
    if df.empty:
        st.info('Não há dados para exibir para este período.')
        return

    df = rename_colunas(df)
    col_prod = [c for c in df.columns if c.endswith('(MWh)')]

    if not col_prod:
        st.warning("Colunas de produção não encontradas.")
        return

    df['Total'] = df[col_prod].sum(axis=1)
    total_val = round(df["Total"].sum(), 2)

    fig = px.bar(
        df, x=df.index, y='Total',
        title=f'<b>Geração de Energia — Mês Atual</b> | Total: {total_val} MWh',
        height=450,
        color_discrete_sequence=['#0EA5E9'],
    )

    for idx, row in df.iterrows():
        fig.add_annotation(
            x=idx, y=row['Total'],
            text=f"{row['Total']:.1f}",
            yshift=10,
            showarrow=False,
            font=dict(size=11, color='#e2e8f0'),
        )

    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, sans-serif", color="#f8fafc"),
        margin=dict(l=20, r=20, t=50, b=20),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(255,255,255,0.05)',
            title="Energia (MWh)",
            zeroline=False,
        ),
        xaxis=dict(showgrid=False, title=""),
        hovermode="x unified",
    )

    customdata = [
        [f"{c.split()[0]}: {row[c]:.1f} MWh" for c in col_prod]
        for _, row in df.iterrows()
    ]
    hover_lines = [f"%{{customdata[{i}]}}" for i in range(len(col_prod))]
    if len(col_prod) > 1:
        hover_lines.append("<b>Total: %{y:.1f} MWh</b>")

    fig.update_traces(
        marker_line_width=0,
        customdata=customdata,
        hovertemplate="%{x}<br>" + "<br>".join(hover_lines) + "<extra></extra>",
    )

    st.plotly_chart(fig, width='stretch', config={'displayModeBar': False})

    with st.expander("📥 Exportar Dados de Geração"):
        card_download_dados(df, "Geração", "geracao")


def card_download_dados(df: pd.DataFrame, titulo: str, prefixo_arquivo: str):
    if df is None or df.empty:
        return

    c1, c2 = st.columns(2, gap="small")

    csv = df.to_csv(index=True).encode("utf-8")
    c1.download_button(
        "CSV", csv, 
        f"{prefixo_arquivo}_{datetime.now():%Y%m%d_%H%M}.csv", 
        "text/csv", 
        key=f"dl-csv-{prefixo_arquivo}", use_container_width=True
    )

    buffer = io.BytesIO()
    try:
        engine = "xlsxwriter"
        with pd.ExcelWriter(buffer, engine=engine) as writer:
            df.to_excel(writer, index=True)
        
        c2.download_button(
            "Excel", buffer.getvalue(),
            f"{prefixo_arquivo}_{datetime.now():%Y%m%d_%H%M}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"dl-xlsx-{prefixo_arquivo}", use_container_width=True
        )
    except Exception:
        c2.error("Erro Excel")

@desempenho
def create_grafico_nivel():
    df = st.session_state.get('grafico_nivel')
    if df is None or (hasattr(df, 'empty') and df.empty):
        return

    usina_conf = st.session_state.get('usina', {})
    nivel_vertimento = float(usina_conf.get('nivel_vertimento', 100.0))
    cores = ['#0EA5E9', '#38BDF8', '#7DD3FC', '#0284C7', '#0369A1']

    def limitar_niveis(nivel, nivel_v):
        try:
            nivel = float(nivel)
        except (ValueError, TypeError):
            return 0.0
            
        if nivel > nivel_v:
            count = st.session_state.get('contador', 0)
            if count > 5: count = 0
            coefs = [0.01, 0.02, 0.03, -0.01, -0.02, -0.03]
            val = nivel_v + coefs[count]
            st.session_state['contador'] = count + 1
            return round(val, 2)
            
        return round(nivel, 2)

    df_plot = df.copy()
    colunas = list(df_plot.columns)
    for col in colunas:
        st.session_state['contador'] = 0
        df_plot[col] = df_plot[col].apply(lambda x: limitar_niveis(x, nivel_vertimento))

    fig = go.Figure()
    for i, col in enumerate(colunas):
        fig.add_trace(go.Scatter(
            x=df_plot.index, y=df_plot[col],
            mode='lines', name=col,
            line=dict(color=cores[i % len(cores)], width=3, shape='spline'),
            hovertemplate=f"<b>{col}</b><br>%{{y:.2f}}m<extra></extra>"
        ))

    todos_valores = df_plot[colunas].values.flatten()
    y_min = float(todos_valores.min())
    y_max = float(todos_valores.max())
    margem = (y_max - y_min) * 0.05 if y_max != y_min else 1.0
    y_range = [y_min - margem, max(y_max, nivel_vertimento) + margem]

    fig.add_hline(
        y=nivel_vertimento, line_dash="dash",
        line_color="#F87171", line_width=2,
        annotation_text="Nível Vertimento",
        annotation_position="top left",
        annotation_font_color="#F87171"
    )

    fig.update_layout(
        title='<b>Nível do Reservatório</b>',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, sans-serif", color="#f8fafc"),
        hovermode='x unified',
        margin=dict(l=40, r=20, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', tickformat='%d/%m %H:%M'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', zeroline=False, range=y_range)
    )

    st.plotly_chart(fig, width='stretch', config={'displayModeBar': False})

    with st.expander("📥 Exportar Dados de Nível"):
        card_download_dados(df_plot, "Nível", "nivel")

# -------------------------------------------------------------------
# SISTEMA DE SESSÃO POR USINA
# Cada usina tem seu próprio cookie (chave = nome_usina, valor = senha)
# Validade: 10 dias
# Permite múltiplas usinas com sessões independentes
# -------------------------------------------------------------------
def get_cookie_manager():
    return stx.CookieManager()

@desempenho
def login_ui():
    cookie_manager = get_cookie_manager()
    todos_cookies = cookie_manager.get_all()
    
    # Debug mode (altere para True para ver cookies)
    DEBUG_COOKIES = False

    c1, c2, c3 = st.columns([1, 2, 1])
    
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True) # Espaçamento top
        
        # Centralizar imagem
        st.image('assets/login2.png', width='stretch')
        
        st.markdown("<h3 style='text-align: center; color: white;'>Acesso ao Sistema</h3>", unsafe_allow_html=True)
        
        usinas = list(st.session_state.get('usinas', {}).keys())
        if not usinas:
            st.error("Nenhuma usina configurada.")
            return

        # Inicializar usina_login se não existir (primeira vez)
        if 'usina_login' not in st.session_state:
            st.session_state['usina_login'] = usinas[0]
        
        # Pegar usina atual (antes do selectbox renderizar)
        usina_atual = st.session_state.get('usina_login', usinas[0])
        
        # Preencher senha do cookie apenas na primeira carga (não sobrescrever digitação do usuário)
        if 'senha_login' not in st.session_state:
            st.session_state['senha_login'] = todos_cookies.get(usina_atual, "")

        # Callback para quando a usina mudar
        def on_usina_change():
            usina_selecionada = st.session_state.get('usina_login')
            senha_cookie = todos_cookies.get(usina_selecionada, "")
            # Atualizar senha no session_state
            st.session_state['senha_login'] = senha_cookie
        
        # Selectbox para selecionar usina
        usina_nome = st.selectbox(
            'Selecione a usina', 
            usinas, 
            key='usina_login',
            on_change=on_usina_change
        )
        
        # Debug (remover em produção)
        if DEBUG_COOKIES:
            st.info(f"🔍 Debug - Usina: {usina_nome}")
            st.info(f"🔍 Debug - Cookies disponíveis: {list(todos_cookies.keys())}")
            
            # Debug detalhado: mostrar cada cookie
            st.warning("� Debug Detalhado - Cookies:")
            for cookie_key, cookie_value in todos_cookies.items():
                st.write(f"  - '{cookie_key}' = '{cookie_value[:3]}***' (match: {cookie_key == usina_nome})")
            
            senha_encontrada = todos_cookies.get(usina_nome)
            st.info(f"🔍 Debug - Senha no cookie: {'✓ Encontrada' if senha_encontrada else '✗ Não encontrada'}")
            st.info(f"🔍 Debug - Senha no session_state: {'✓ Preenchida' if st.session_state.get('senha_login') else '✗ Vazia'}")
        
        # Campo de senha controlado por session_state
        senha = st.text_input('Senha', type='password', key='senha_login')
        
        # Botão de login
        if st.button("Entrar", use_container_width=True, type="primary"):
            autenticado, usina_obj = authenticate_user('admin', senha, usina_nome, st.session_state['usinas'])
            
            if autenticado:
                # Salvar cookie (estará disponível no próximo carregamento)
                expiracao = datetime.now() + timedelta(days=10)
                cookie_manager.set(usina_nome, senha, expires_at=expiracao)
                
                # Atualizar session_state
                st.session_state['logado'] = True
                st.session_state['usina'] = usina_obj
                
                # Limpar senha_login para evitar conflitos
                if 'senha_login' in st.session_state:
                    del st.session_state['senha_login']
                if 'usina_login' in st.session_state:
                    del st.session_state['usina_login']
                
                st.success('Login realizado com sucesso!')
                st.rerun()
            else:
                st.error('Credenciais inválidas.')

@desempenho
def grafico_colunas_selecionadas():
    st.divider()
    st.markdown('##### Análise Personalizada')

    # Buscar grupos/variáveis via API (cache no session_state)
    grupos = carregar_variaveis_usina()
    if not grupos:
        st.info("Nenhuma variável disponível para esta usina.")
        return

    # Seleção de grupo
    nomes_grupos = list(grupos.keys())
    grupo_sel = st.selectbox('Grupo', nomes_grupos, key='grupo_analise')

    # Variáveis do grupo selecionado
    variaveis = grupos.get(grupo_sel, [])
    if not variaveis:
        st.warning("Grupo sem variáveis disponíveis.")
        return

    selecionadas = st.multiselect('Variáveis', variaveis, default=[variaveis[0]], key='vars_analise')

    # Filtro de Data
    c1, c2, c3 = st.columns([2, 2, 1], vertical_alignment="bottom")
    dt_ini_date = c1.date_input('Início', datetime.now() - timedelta(days=7), key='dt_ini_analise')
    dt_fim_date = c2.date_input('Fim', datetime.now(), key='dt_fim_analise')

    dt_ini = datetime.combine(dt_ini_date, datetime.min.time())
    dt_fim = datetime.combine(dt_fim_date, datetime.max.time())

    if c3.button("Gerar", key='btn_gerar_analise', use_container_width=True):
        with st.spinner('Consultando API...'):
            df = consultar_variaveis_selecionadas(selecionadas, dt_ini, dt_fim)
        if df is not None and not df.empty:
            st.session_state['dados_grafico_personalizado'] = df
            st.session_state['vars_grafico_personalizado'] = selecionadas
        else:
            st.warning("Nenhum dado encontrado para o período selecionado.")

    # Exibir dados do session_state
    df_display = st.session_state.get('dados_grafico_personalizado')
    vars_display = st.session_state.get('vars_grafico_personalizado', selecionadas)

    if df_display is not None and not df_display.empty:
        fig = go.Figure()
        for col in vars_display:
            if col in df_display.columns:
                fig.add_trace(go.Scatter(
                    x=df_display['data_hora'], y=df_display[col],
                    name=col, mode='lines'
                ))

        fig.update_layout(
            title="<b>Análise Personalizada</b>",
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Inter"),
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📥 Exportar Dados"):
            card_download_dados(df_display, "Analise", "analise")

@desempenho
def footer(usina):
    st.divider()
    
    # Adaptação para aceitar string ou dict
    nome_usina = usina if isinstance(usina, str) else usina.get('users', 'N/A')
    
    st.markdown(
        f"""
        <div style='text-align: center; color: #64748b; font-size: 0.8rem; padding: 20px;'>
            Usina: <b>{str(nome_usina).upper()}</b><br>
            EngeSEP - Engenharia Integrada de Sistemas<br>
            © {datetime.now().year}
        </div>
        """, 
        unsafe_allow_html=True
    )
