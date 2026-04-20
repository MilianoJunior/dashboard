'''
# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. desempenho (decorator)     → Mede tempo e trata erros
# 2. _get_mock_data             → Dados fictícios realistas (PCH)
# 3. _gerar_grafico_barras      → Matplotlib → base64 (barras mensais)
# 4. _gerar_grafico_comparativo → Matplotlib → base64 (barras duplas)
# 5. _gerar_grafico_linhas      → Matplotlib → base64 (curva diária)
# 6. _gerar_mini_sparkline      → Matplotlib → base64 (mini gráfico p/ card)
# 7. _build_html                → Monta HTML completo com CSS inline
# 8. gerar_relatorio            → WeasyPrint renderiza HTML → PDF
# -------------------------------------------------------------------
'''
import os
import io
import base64
import time
import functools
import random

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

from weasyprint import HTML

# -------------------------------------------------------------------
# CONFIGURAÇÕES E CONSTANTES
# -------------------------------------------------------------------
DEBUG = True
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_SAIDA = os.path.join(BASE_DIR, "Relatorio_Premium.pdf")
contador_execucoes = 0

MESES_TODOS = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN",
               "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]

# Paleta moderna
C = {
    "bg_dark":    "#0F172A",
    "bg_card":    "#1E293B",
    "bg_surface": "#334155",
    "accent":     "#F59E0B",
    "accent2":    "#3B82F6",
    "accent3":    "#10B981",
    "danger":     "#EF4444",
    "text":       "#F8FAFC",
    "text_dim":   "#94A3B8",
    "text_muted": "#64748B",
    "border":     "#475569",
    "white":      "#FFFFFF",
    "table_row1": "#1E293B",
    "table_row2": "#0F172A",
}


# -------------------------------------------------------------------
# FUNÇÕES AUXILIARES
# -------------------------------------------------------------------

def desempenho(func):
    """Decorator para log de tempo e tratamento de erros."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        global contador_execucoes
        contador_execucoes += 1
        try:
            inicio = time.time()
            resultado = func(*args, **kwargs)
            duracao = time.time() - inicio
            if DEBUG:
                print(f"[{contador_execucoes}] {func.__name__} ({duracao:.4f}s)")
            return resultado
        except Exception as e:
            raise RuntimeError(f"Erro em {func.__name__}: {e}") from e
    return wrapper


def _get_mock_data():
    """Dados fictícios realistas simulando PCH-PIRA."""
    random.seed(42)

    geracao = {}
    meses_com_dados = ["JAN", "FEV", "MAR", "ABR"]
    for mes in MESES_TODOS:
        if mes in meses_com_dados:
            base = random.uniform(80, 200)
            geracao[mes] = [round(base + random.uniform(-60, 300), 2) for _ in range(31)]
        else:
            geracao[mes] = [0.0] * 31

    # Ajustar dias inexistentes
    for d in [28, 29, 30]:
        geracao["FEV"][d] = 0.0
    geracao["ABR"][30] = 0.0

    gf_mensal = {
        "JAN": 9686.88, "FEV": 8749.44, "MAR": 9686.88, "ABR": 9374.40,
        "MAI": 9686.88, "JUN": 9374.40, "JUL": 9686.88, "AGO": 9686.88,
        "SET": 9374.40, "OUT": 9686.88, "NOV": 9374.40, "DEZ": 9686.88
    }

    totais_mes = {m: round(sum(geracao[m]), 2) for m in MESES_TODOS}
    perf_mes = {}
    for m in MESES_TODOS:
        if totais_mes[m] > 0:
            perf_mes[m] = round(totais_mes[m] / gf_mensal[m] * 100, 1)
        else:
            perf_mes[m] = 0.0

    geracao_anual = sum(totais_mes.values())
    gf_anual = sum(gf_mensal.values())
    meses_op = [m for m in MESES_TODOS if totais_mes[m] > 0]
    media = geracao_anual / len(meses_op) if meses_op else 0
    pico = max(meses_op, key=lambda m: totais_mes[m]) if meses_op else "-"

    return {
        "meta": {
            "ano": "2026", "cliente": "IPIRA ENERGIA S.A", "usina": "PCH-PIRA",
            "uc": "N/D", "periodo": "01/01/2026 — 31/12/2026",
            "emissao": "16/04/2026", "meta_dia": 312.48, "gf_mwh": 13.02
        },
        "meses_op": meses_op,
        "geracao": geracao,
        "totais": totais_mes,
        "gf": gf_mensal,
        "perf": perf_mes,
        "resumo": {
            "anual": geracao_anual, "gf_anual": gf_anual,
            "perf_global": round(geracao_anual / gf_anual * 100, 1) if gf_anual else 0,
            "media": media, "pico_mes": pico, "pico_val": totais_mes.get(pico, 0),
            "dias_acima_meta": sum(1 for m in meses_op for v in geracao[m] if v >= 312.48),
            "dias_operados": sum(1 for m in meses_op for v in geracao[m] if v > 0),
        }
    }


# -------------------------------------------------------------------
# GRÁFICOS (Matplotlib → base64)
# -------------------------------------------------------------------

def _fig_to_b64(fig):
    """Converte Figure do Matplotlib em string base64 para embed no HTML."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=180, bbox_inches='tight',
                facecolor=C["bg_card"], edgecolor='none', transparent=False)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')


def _style_ax(ax):
    """Aplica estilo dark mode padrão ao eixo."""
    ax.set_facecolor(C["bg_card"])
    ax.tick_params(colors=C["text_dim"], labelsize=7)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color(C["border"])
    ax.spines['left'].set_color(C["border"])
    ax.yaxis.label.set_color(C["text_dim"])
    ax.xaxis.label.set_color(C["text_dim"])


def _gerar_grafico_barras(totais, meses):
    """Barras mensais — geração anual."""
    fig, ax = plt.subplots(figsize=(8, 3))
    fig.patch.set_facecolor(C["bg_card"])
    _style_ax(ax)

    vals = [totais.get(m, 0) for m in meses]
    cores = [C["accent"] if v > 0 else C["bg_surface"] for v in vals]
    bars = ax.bar(meses, vals, color=cores, width=0.6, edgecolor='none', zorder=3)

    for bar, v in zip(bars, vals):
        if v > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(vals) * 0.03,
                    f"{v:,.0f}".replace(",", "."), ha='center', va='bottom',
                    fontsize=6, color=C["text"], fontweight='bold')

    ax.set_ylim(0, max(vals) * 1.25 if max(vals) > 0 else 100)
    ax.grid(axis='y', color=C["border"], alpha=0.3, linestyle='--', zorder=0)
    ax.set_axisbelow(True)
    return _fig_to_b64(fig)


def _gerar_grafico_comparativo(dados_atual, dados_ant, mes_at, mes_an):
    """Barras duplas — mês atual vs anterior."""
    fig, ax = plt.subplots(figsize=(8, 3.5))
    fig.patch.set_facecolor(C["bg_card"])
    _style_ax(ax)

    dias = list(range(1, 32))
    x = np.arange(31)
    w = 0.38
    ax.bar(x - w / 2, dados_ant, w, label=f"{mes_an}", color=C["bg_surface"], edgecolor='none', zorder=3)
    ax.bar(x + w / 2, dados_atual, w, label=f"{mes_at}", color=C["accent2"], edgecolor='none', zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(dias, fontsize=5, color=C["text_dim"])
    ax.legend(fontsize=7, facecolor=C["bg_card"], edgecolor=C["border"],
              labelcolor=C["text_dim"], loc='upper right')
    ax.grid(axis='y', color=C["border"], alpha=0.3, linestyle='--', zorder=0)
    return _fig_to_b64(fig)


def _gerar_grafico_linhas(dados_dias, titulo, destaque=False):
    """Curva de geração diária de um mês."""
    fig, ax = plt.subplots(figsize=(8, 3))
    fig.patch.set_facecolor(C["bg_card"])
    _style_ax(ax)

    dias = list(range(1, len(dados_dias) + 1))
    cor = C["accent3"] if not destaque else C["accent"]

    # Área sob a curva
    ax.fill_between(dias, dados_dias, alpha=0.15, color=cor, zorder=2)
    ax.plot(dias, dados_dias, color=cor, marker='o', markersize=3,
            linewidth=1.5, zorder=3, markerfacecolor=cor, markeredgecolor=C["bg_card"], markeredgewidth=0.5)

    # Anotar pico
    max_val = max(dados_dias)
    max_idx = dados_dias.index(max_val) + 1
    if max_val > 0:
        ax.annotate(f"{max_val:,.2f}".replace(",", "."),
                    xy=(max_idx, max_val), xytext=(max_idx, max_val * 1.12),
                    fontsize=7, color=C["accent"], fontweight='bold', ha='center',
                    arrowprops=dict(arrowstyle='->', color=C["accent"], lw=0.8))

    ax.set_xlim(0.5, 31.5)
    ax.set_xticks(range(1, 32, 2))
    ax.set_ylim(0, max(dados_dias) * 1.3 if max(dados_dias) > 0 else 100)
    ax.grid(axis='y', color=C["border"], alpha=0.3, linestyle='--', zorder=0)
    ax.set_title(titulo, fontsize=8, fontweight='bold', color=C["text"], loc='left', pad=8)

    if destaque:
        ax.text(0.98, 0.92, "★ MELHOR MÊS", transform=ax.transAxes,
                fontsize=7, color=C["accent"], ha='right', va='top', fontweight='bold')

    return _fig_to_b64(fig)


def _gerar_sparkline(valores, cor=None):
    """Mini gráfico sparkline para cards KPI."""
    cor = cor or C["accent3"]
    fig, ax = plt.subplots(figsize=(2.2, 0.6))
    fig.patch.set_facecolor('none')
    ax.set_facecolor('none')
    ax.fill_between(range(len(valores)), valores, alpha=0.2, color=cor)
    ax.plot(valores, color=cor, linewidth=1.5)
    ax.axis('off')
    ax.margins(x=0, y=0.1)
    return _fig_to_b64(fig)


# -------------------------------------------------------------------
# HTML + CSS
# -------------------------------------------------------------------

CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

@page {{
    size: A4;
    margin: 0;
}}

* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: 'Inter', -apple-system, 'Segoe UI', sans-serif;
    color: {C["text"]};
    background: {C["bg_dark"]};
    font-size: 9px;
    line-height: 1.4;
}}

.page {{
    width: 210mm;
    min-height: 297mm;
    padding: 18mm 16mm 14mm 16mm;
    page-break-after: always;
    position: relative;
    background: {C["bg_dark"]};
}}

.page:last-child {{
    page-break-after: auto;
}}

/* ---------- COVER ---------- */
.cover {{
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    height: 100%;
    padding: 0;
}}

.cover-top {{
    text-align: center;
    padding-top: 60px;
}}

.cover-logo {{
    font-size: 11px;
    font-weight: 700;
    color: {C["accent"]};
    letter-spacing: 4px;
    text-transform: uppercase;
    margin-bottom: 50px;
}}

.cover-title {{
    font-size: 34px;
    font-weight: 900;
    color: {C["white"]};
    line-height: 1.15;
    margin-bottom: 10px;
    letter-spacing: -0.5px;
}}

.cover-subtitle {{
    font-size: 13px;
    font-weight: 500;
    color: {C["text_dim"]};
    letter-spacing: 3px;
    text-transform: uppercase;
    margin-bottom: 20px;
}}

.cover-year {{
    font-size: 56px;
    font-weight: 900;
    background: linear-gradient(135deg, {C["accent"]}, {C["accent3"]});
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 10px;
}}

.cover-divider {{
    width: 80px;
    height: 3px;
    background: {C["accent"]};
    margin: 0 auto 50px auto;
    border-radius: 2px;
}}

.cover-meta {{
    background: {C["bg_card"]};
    border-radius: 12px;
    padding: 20px 24px;
    border: 1px solid {C["border"]};
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
}}

.cover-meta-item {{
    border-left: 3px solid {C["accent"]};
    padding-left: 12px;
}}

.cover-meta-label {{
    font-size: 8px;
    font-weight: 600;
    color: {C["text_muted"]};
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 3px;
}}

.cover-meta-value {{
    font-size: 12px;
    font-weight: 700;
    color: {C["text"]};
}}

.cover-meta-sub {{
    font-size: 9px;
    color: {C["accent"]};
    font-weight: 500;
}}

/* ---------- SECTION HEADER ---------- */
.section-header {{
    margin-bottom: 16px;
}}

.section-tag {{
    font-size: 8px;
    font-weight: 700;
    color: {C["accent"]};
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 4px;
}}

.section-title {{
    font-size: 20px;
    font-weight: 800;
    color: {C["white"]};
    margin-bottom: 2px;
}}

.section-desc {{
    font-size: 9px;
    color: {C["text_muted"]};
}}

/* ---------- KPI CARDS ---------- */
.kpi-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 10px;
    margin-bottom: 14px;
}}

.kpi-card {{
    background: {C["bg_card"]};
    border-radius: 10px;
    padding: 14px 16px;
    border: 1px solid {C["border"]};
    position: relative;
    overflow: hidden;
}}

.kpi-card-wide {{
    grid-column: span 2;
}}

.kpi-label {{
    font-size: 7.5px;
    font-weight: 600;
    color: {C["text_muted"]};
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 6px;
}}

.kpi-value {{
    font-size: 22px;
    font-weight: 800;
    color: {C["white"]};
    line-height: 1.1;
}}

.kpi-unit {{
    font-size: 10px;
    font-weight: 500;
    color: {C["text_dim"]};
    margin-left: 3px;
}}

.kpi-sub {{
    font-size: 8px;
    color: {C["text_muted"]};
    margin-top: 4px;
}}

.kpi-sparkline {{
    position: absolute;
    bottom: 0;
    right: 0;
    opacity: 0.6;
}}

.badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 8px;
    font-weight: 700;
}}

.badge-green {{
    background: rgba(16, 185, 129, 0.15);
    color: {C["accent3"]};
}}

.badge-red {{
    background: rgba(239, 68, 68, 0.15);
    color: {C["danger"]};
}}

.badge-amber {{
    background: rgba(245, 158, 11, 0.15);
    color: {C["accent"]};
}}

/* ---------- CHART ---------- */
.chart-container {{
    background: {C["bg_card"]};
    border-radius: 10px;
    padding: 14px;
    border: 1px solid {C["border"]};
    margin-bottom: 12px;
}}

.chart-title {{
    font-size: 9px;
    font-weight: 700;
    color: {C["text_dim"]};
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
}}

.chart-img {{
    width: 100%;
    border-radius: 6px;
}}

/* ---------- TABLE ---------- */
.data-table {{
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 7px;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid {C["border"]};
}}

.data-table th {{
    background: {C["bg_card"]};
    color: {C["accent"]};
    font-weight: 700;
    padding: 6px 3px;
    text-align: center;
    font-size: 7.5px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 2px solid {C["accent"]};
}}

.data-table td {{
    padding: 3px 2px;
    text-align: center;
    border-bottom: 1px solid rgba(71, 85, 105, 0.4);
    color: {C["text"]};
    font-variant-numeric: tabular-nums;
}}

.data-table tr:nth-child(odd) td {{
    background: {C["table_row1"]};
}}

.data-table tr:nth-child(even) td {{
    background: {C["table_row2"]};
}}

.data-table .td-val {{
    font-weight: 600;
    font-size: 7.5px;
}}

.data-table .td-pct {{
    font-size: 6px;
    color: {C["text_muted"]};
}}

.data-table .row-total td {{
    background: {C["accent"]} !important;
    color: {C["bg_dark"]};
    font-weight: 800;
    font-size: 7.5px;
    border: none;
}}

.data-table .row-gf td {{
    background: {C["bg_surface"]} !important;
    color: {C["text_dim"]};
    font-weight: 600;
    border: none;
}}

.data-table .row-perf td {{
    background: {C["bg_card"]} !important;
    font-weight: 700;
    border: none;
}}

.td-dia {{
    font-weight: 700;
    color: {C["accent"]} !important;
    background: {C["bg_card"]} !important;
}}

/* ---------- SUMMARY BAR ---------- */
.summary-bar {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    margin-top: 10px;
    margin-bottom: 8px;
}}

.summary-item {{
    background: {C["bg_card"]};
    border-radius: 8px;
    padding: 8px 10px;
    border: 1px solid {C["border"]};
    text-align: center;
}}

.summary-item-label {{
    font-size: 7px;
    color: {C["text_muted"]};
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

.summary-item-value {{
    font-size: 12px;
    font-weight: 800;
    color: {C["white"]};
    margin-top: 2px;
}}

/* ---------- PAGE FOOTER ---------- */
.page-footer {{
    position: absolute;
    bottom: 10mm;
    left: 16mm;
    right: 16mm;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-top: 1px solid {C["border"]};
    padding-top: 6px;
}}

.page-footer-text {{
    font-size: 7px;
    color: {C["text_muted"]};
}}

.page-footer-page {{
    font-size: 7px;
    font-weight: 700;
    color: {C["accent"]};
}}

/* ---------- SUMARIO ---------- */
.toc-list {{
    list-style: none;
    margin-top: 12px;
}}

.toc-item {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding: 10px 14px;
    border-radius: 8px;
    margin-bottom: 6px;
    background: {C["bg_card"]};
    border: 1px solid {C["border"]};
    transition: all 0.2s;
}}

.toc-item-num {{
    font-size: 14px;
    font-weight: 800;
    color: {C["accent"]};
    margin-right: 10px;
    min-width: 20px;
}}

.toc-item-title {{
    flex: 1;
    font-size: 10px;
    font-weight: 600;
    color: {C["text"]};
}}

.toc-item-page {{
    font-size: 10px;
    font-weight: 700;
    color: {C["text_dim"]};
    margin-left: 10px;
}}

/* ---------- SPLIT CHARTS ---------- */
.chart-row {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
}}
"""


def _build_html(dados):
    """Monta o HTML completo de todas as páginas do relatório."""
    meta = dados["meta"]
    resumo = dados["resumo"]
    meses_op = dados["meses_op"]

    # Gerar sparklines para cards
    vals_mensais = [dados["totais"].get(m, 0) for m in meses_op]
    spark_geracao = _gerar_sparkline(vals_mensais, C["accent3"])
    spark_perf = _gerar_sparkline([dados["perf"].get(m, 0) for m in meses_op], C["accent2"])

    # Gerar gráficos
    chart_barras = _gerar_grafico_barras(dados["totais"], MESES_TODOS)

    chart_comp = ""
    if len(meses_op) >= 2:
        chart_comp = _gerar_grafico_comparativo(
            dados["geracao"][meses_op[-1]], dados["geracao"][meses_op[-2]],
            meses_op[-1], meses_op[-2]
        )

    # Curvas diárias
    curvas = []
    for mes in meses_op:
        titulo = f"GERAÇÃO DE {mes} {meta['ano']} (MWh)"
        destaque = (mes == resumo["pico_mes"])
        curvas.append((mes, _gerar_grafico_linhas(dados["geracao"][mes], titulo, destaque), destaque))

    # Performance badge
    pg = resumo["perf_global"]
    badge_class = "badge-green" if pg >= 100 else ("badge-amber" if pg >= 50 else "badge-red")
    badge_text = "ACIMA DA META" if pg >= 100 else ("PARCIAL" if pg >= 50 else "ABAIXO DA META")

    # ==================== PÁGINA 1: CAPA ====================
    page1 = f"""
    <div class="page cover">
        <div class="cover-top">
            <div class="cover-logo">⚡ ENGESEP · ENGENHARIA INTEGRADA</div>
            <div class="cover-title">RELATÓRIO DE GESTÃO<br>INTEGRADA</div>
            <div class="cover-subtitle">Performance Operacional</div>
            <div class="cover-year">{meta["ano"]}</div>
            <div class="cover-divider"></div>
        </div>
        <div class="cover-meta">
            <div class="cover-meta-item">
                <div class="cover-meta-label">Cliente Parceiro</div>
                <div class="cover-meta-value">{meta["cliente"]}</div>
                <div class="cover-meta-sub">{meta["usina"]}</div>
            </div>
            <div class="cover-meta-item">
                <div class="cover-meta-label">Período Analisado</div>
                <div class="cover-meta-value">{meta["periodo"]}</div>
            </div>
            <div class="cover-meta-item">
                <div class="cover-meta-label">Unidade Consumidora</div>
                <div class="cover-meta-value">{meta["uc"]}</div>
            </div>
            <div class="cover-meta-item">
                <div class="cover-meta-label">Emissão do Documento</div>
                <div class="cover-meta-value">{meta["emissao"]}</div>
            </div>
        </div>
    </div>
    """

    # ==================== PÁGINA 2: SUMÁRIO ====================
    toc_items = [
        ("01", "CAPA", "1"),
        ("02", "SUMÁRIO", "2"),
        ("03", "TABELA DE GERAÇÃO OPERACIONAL (MWh)", "3"),
        ("04", "ANÁLISE DE PERFORMANCE OPERACIONAL", "4"),
        ("05", "CURVAS DE GERAÇÃO DIÁRIA POR MÊS", "5"),
    ]
    toc_html = ""
    for num, titulo, pag in toc_items:
        toc_html += f"""
        <div class="toc-item">
            <span class="toc-item-num">{num}</span>
            <span class="toc-item-title">{titulo}</span>
            <span class="toc-item-page">{pag}</span>
        </div>"""

    page2 = f"""
    <div class="page">
        <div class="section-header">
            <div class="section-tag">Navegação</div>
            <div class="section-title">Sumário</div>
        </div>
        <div class="toc-list">{toc_html}</div>
        <div class="page-footer">
            <span class="page-footer-text">{meta["cliente"]} · {meta["usina"]} · {meta["ano"]}</span>
            <span class="page-footer-page">02</span>
        </div>
    </div>
    """

    # ==================== PÁGINA 3: TABELA ====================
    # Gerar linhas da tabela
    meses = MESES_TODOS
    rows_html = ""
    for dia in range(1, 32):
        cells = f'<td class="td-dia">{dia}º</td>'
        for m in meses:
            v = dados["geracao"][m][dia - 1]
            if v > 0:
                gf_dia = dados["gf"][m] / 31
                pct = v / gf_dia * 100
                cells += f'<td><span class="td-val">{v:,.2f}</span><br><span class="td-pct">{pct:.1f}%</span></td>'.replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                cells += '<td></td>'
        rows_html += f'<tr>{cells}</tr>\n'

    # Linha TOTAL
    total_cells = '<td class="td-dia" style="font-weight:900">TOTAL</td>'
    for m in meses:
        v = dados["totais"][m]
        total_cells += f'<td>{v:,.2f}</td>'.replace(",", "X").replace(".", ",").replace("X", ".")
    rows_html += f'<tr class="row-total">{total_cells}</tr>\n'

    # Linha G. FÍSICA
    gf_cells = '<td>G. FÍSICA</td>'
    for m in meses:
        v = dados["gf"][m]
        gf_cells += f'<td>{v:,.2f}</td>'.replace(",", "X").replace(".", ",").replace("X", ".")
    rows_html += f'<tr class="row-gf">{gf_cells}</tr>\n'

    # Linha PERF. %
    perf_cells = '<td>PERF. %</td>'
    for m in meses:
        p = dados["perf"][m]
        if p > 0:
            color = C["accent3"] if p >= 100 else (C["accent"] if p >= 50 else C["danger"])
            perf_cells += f'<td style="color:{color}">{p:.1f}%</td>'
        else:
            perf_cells += f'<td style="color:{C["text_muted"]}">—</td>'
    rows_html += f'<tr class="row-perf">{perf_cells}</tr>\n'

    header_cells = '<th>DIA</th>' + ''.join(f'<th>{m}</th>' for m in meses)

    page3 = f"""
    <div class="page">
        <div class="section-header">
            <div class="section-tag">Seção 03</div>
            <div class="section-title">Geração Operacional ({meta["ano"]})</div>
            <div class="section-desc">Valores em MWh · Percentual relativo à Garantia Física diária</div>
        </div>
        <table class="data-table">
            <thead><tr>{header_cells}</tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        <div class="summary-bar">
            <div class="summary-item">
                <div class="summary-item-label">Meta Diária</div>
                <div class="summary-item-value">{meta["meta_dia"]} MW</div>
            </div>
            <div class="summary-item">
                <div class="summary-item-label">GF Anual</div>
                <div class="summary-item-value">{resumo["gf_anual"]:,.0f} MW</div>
            </div>
            <div class="summary-item">
                <div class="summary-item-label">Geração Anual</div>
                <div class="summary-item-value" style="color:{C["accent2"]}">{resumo["anual"]:,.0f} MW</div>
            </div>
            <div class="summary-item">
                <div class="summary-item-label">Perf. Global</div>
                <div class="summary-item-value"><span class="badge {badge_class}">{resumo["perf_global"]}%</span></div>
            </div>
        </div>
        <div class="page-footer">
            <span class="page-footer-text">{meta["cliente"]} · {meta["usina"]} · {meta["ano"]}</span>
            <span class="page-footer-page">03</span>
        </div>
    </div>
    """

    # ==================== PÁGINA 4: PERFORMANCE ====================
    comp_section = ""
    if chart_comp:
        comp_section = f"""
        <div class="chart-container">
            <div class="chart-title">Comparativo Diário — {meses_op[-1]} vs {meses_op[-2]} (MWh)</div>
            <img class="chart-img" src="data:image/png;base64,{chart_comp}">
        </div>"""

    page4 = f"""
    <div class="page">
        <div class="section-header">
            <div class="section-tag">Seção 04</div>
            <div class="section-title">Análise de Performance</div>
            <div class="section-desc">Comparativo e histórico do ano {meta["ano"]}</div>
        </div>
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">Geração Total Anual</div>
                <div class="kpi-value">{resumo["anual"]:,.2f}<span class="kpi-unit">MWh</span></div>
                <div class="kpi-sub">Acumulado até {meses_op[-1] if meses_op else '—'}</div>
                <img class="kpi-sparkline" src="data:image/png;base64,{spark_geracao}" width="90">
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Média Mensal</div>
                <div class="kpi-value">{resumo["media"]:,.2f}<span class="kpi-unit">MWh/mês</span></div>
                <div class="kpi-sub">{len(meses_op)} meses operados</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Pico de Geração</div>
                <div class="kpi-value">{resumo["pico_mes"]}</div>
                <div class="kpi-sub">{resumo["pico_val"]:,.2f} MWh</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Dias Acima da Meta</div>
                <div class="kpi-value">{resumo["dias_acima_meta"]}<span class="kpi-unit">dias</span></div>
                <div class="kpi-sub">de {resumo["dias_operados"]} operados</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Performance Global</div>
                <div class="kpi-value">{resumo["perf_global"]}%</div>
                <div class="kpi-sub"><span class="badge {badge_class}">{badge_text}</span></div>
                <img class="kpi-sparkline" src="data:image/png;base64,{spark_perf}" width="90">
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Garantia Física</div>
                <div class="kpi-value">{meta["gf_mwh"]}<span class="kpi-unit">MWh</span></div>
                <div class="kpi-sub">GF Anual: {resumo["gf_anual"]:,.0f} MW</div>
            </div>
        </div>
        <div class="chart-container">
            <div class="chart-title">Comparativo Anual — Geração por Mês (MWh)</div>
            <img class="chart-img" src="data:image/png;base64,{chart_barras}">
        </div>
        {comp_section}
        <div class="page-footer">
            <span class="page-footer-text">{meta["cliente"]} · {meta["usina"]} · {meta["ano"]}</span>
            <span class="page-footer-page">04</span>
        </div>
    </div>
    """

    # ==================== PÁGINAS 5+: CURVAS DIÁRIAS ====================
    pages_curvas = ""
    graficos_por_pagina = 3
    page_num = 5

    for idx in range(0, len(curvas), graficos_por_pagina):
        batch = curvas[idx:idx + graficos_por_pagina]
        charts_html = ""
        for mes, b64, destaque in batch:
            star = ' <span style="color:' + C["accent"] + '; font-weight:800">★ MELHOR MÊS</span>' if destaque else ""
            charts_html += f"""
            <div class="chart-container">
                <div class="chart-title">Geração de {mes} {meta["ano"]} (MWh){star}</div>
                <img class="chart-img" src="data:image/png;base64,{b64}">
            </div>"""

        part_num = (idx // graficos_por_pagina) + 1
        total_parts = -(-len(curvas) // graficos_por_pagina)

        pages_curvas += f"""
        <div class="page">
            <div class="section-header">
                <div class="section-tag">Seção 05 · Parte {part_num}/{total_parts}</div>
                <div class="section-title">Curvas de Geração Diária</div>
                <div class="section-desc">Detalhamento dia a dia dos meses operados</div>
            </div>
            {charts_html}
            <div class="page-footer">
                <span class="page-footer-text">{meta["cliente"]} · {meta["usina"]} · {meta["ano"]}</span>
                <span class="page-footer-page">{page_num:02d}</span>
            </div>
        </div>
        """
        page_num += 1

    # ==================== MONTAR HTML ====================
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <style>{CSS}</style>
</head>
<body>
{page1}
{page2}
{page3}
{page4}
{pages_curvas}
</body>
</html>"""

    return html


# -------------------------------------------------------------------
# ORQUESTRADOR
# -------------------------------------------------------------------

@desempenho
def gerar_relatorio(pdf_filename: str, dados: dict = None):
    """Gera o PDF premium via WeasyPrint (HTML → PDF)."""
    if dados is None:
        dados = _get_mock_data()

    html_content = _build_html(dados)

    # Salvar HTML para debug (opcional)
    html_debug = pdf_filename.replace('.pdf', '.html')
    with open(html_debug, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # Renderizar PDF
    HTML(string=html_content, base_url=BASE_DIR).write_pdf(pdf_filename)
    return pdf_filename


# -------------------------------------------------------------------
# EXECUÇÃO
# -------------------------------------------------------------------
if __name__ == "__main__":
    path = gerar_relatorio(ARQUIVO_SAIDA)
    print(f"PDF Premium gerado: {path}")
