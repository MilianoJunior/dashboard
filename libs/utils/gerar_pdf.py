'''
# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. desempenho (decorator)       → Mede tempo e trata erros
# 2. _get_mock_data               → Dados fictícios p/ teste
# 3. _criar_capa                  → Capa com fundo escuro e metadados em grid
# 4. _criar_sumario               → Índice com linha e pontos preenchidos
# 5. _criar_tabela_geracao        → Tabela 12 meses com valor+% e rodapé
# 6. _criar_pagina_performance    → Gráfico barras anual + comparativo diário
# 7. _criar_curvas_diarias        → Gráficos de linha por mês operado
# 8. _gerar_grafico_barras        → Util: gráfico de barras via matplotlib
# 9. _gerar_grafico_linhas        → Util: gráfico de linhas via matplotlib
# 10. _gerar_grafico_comparativo  → Util: gráfico barras duplas
# 11. _rodape_pagina              → Rodapé "Seção X - ..."
# 12. gerar_relatorio             → Orquestra tudo e salva o PDF
# -------------------------------------------------------------------
'''
import os
import io
import time
import functools
import tempfile
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, KeepTogether
)
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus.flowables import HRFlowable
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# -------------------------------------------------------------------
# CONFIGURAÇÕES E CONSTANTES
# -------------------------------------------------------------------
DEBUG = True
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_SAIDA = os.path.join(BASE_DIR, "Relatorio_Teste.pdf")
contador_execucoes = 0

# Cores do relatório
COR_AZUL_ESCURO = "#002B5E"
COR_LARANJA = "#E67E22"
COR_DOURADO = "#DAA520"
COR_FUNDO_HEADER = "#FDEFEA"
COR_CINZA_CLARO = "#F4F6F6"
COR_VERDE = "#27AE60"
COR_VERMELHO = "#E74C3C"

MESES_TODOS = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN",
               "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]

PAGE_W, PAGE_H = A4  # 595.27, 841.89

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
            raise RuntimeError(f"Erro no {func.__name__}: {e}") from e
    return wrapper


def _get_mock_data():
    """Dados fictícios simulando PCH-PIRA para teste visual."""
    import random
    random.seed(42)

    geracao = {}
    meses_com_dados = ["JAN", "FEV", "MAR", "ABR"]
    for mes in MESES_TODOS:
        if mes in meses_com_dados:
            geracao[mes] = [round(random.uniform(20, 480), 2) for _ in range(31)]
        else:
            geracao[mes] = [0.0] * 31

    # FEV tem 28 dias — zerar 29,30,31
    for d in [28, 29, 30]:
        geracao["FEV"][d] = 0.0

    # ABR tem 30 dias — zerar dia 31
    geracao["ABR"][30] = 0.0

    # Garantia física mensal (MW)
    gf_mensal = {
        "JAN": 9686.88, "FEV": 8749.44, "MAR": 9686.88, "ABR": 9374.40,
        "MAI": 9686.88, "JUN": 9374.40, "JUL": 9686.88, "AGO": 9686.88,
        "SET": 9374.40, "OUT": 9686.88, "NOV": 9374.40, "DEZ": 9686.88
    }

    totais_mes = {m: round(sum(geracao[m]), 2) for m in MESES_TODOS}
    perf_mes = {}
    for m in MESES_TODOS:
        if totais_mes[m] > 0:
            perf_mes[m] = f"{totais_mes[m] / gf_mensal[m] * 100:.1f}%"
        else:
            perf_mes[m] = "-"

    geracao_anual = sum(totais_mes.values())
    gf_anual = sum(gf_mensal.values())
    meses_operados = [m for m in MESES_TODOS if totais_mes[m] > 0]
    media_mensal = geracao_anual / len(meses_operados) if meses_operados else 0
    pico_mes = max(meses_operados, key=lambda m: totais_mes[m]) if meses_operados else "-"

    return {
        "METADADOS": {
            "ano": "2026",
            "cliente": "IPIRA ENERGIA S.A",
            "usina": "PCH-PIRA",
            "unidade_consumidora": "N/D",
            "periodo": "01/01/2026 ATÉ 31/12/2026",
            "emissao": "16/04/2026",
            "meta_dia_mw": 312.48,
            "gf_mwh": 13.02
        },
        "MESES_TODOS": MESES_TODOS,
        "MESES_OPERADOS": meses_operados,
        "GERACAO_DIARIA": geracao,
        "TOTAIS_MES": totais_mes,
        "GF_MENSAL": gf_mensal,
        "PERF_MES": perf_mes,
        "RESUMO": {
            "geracao_anual": geracao_anual,
            "gf_anual": gf_anual,
            "perf_global": f"{geracao_anual / gf_anual * 100:.1f}%" if gf_anual else "0%",
            "media_mensal": media_mensal,
            "pico_mes": pico_mes,
            "pico_valor": totais_mes.get(pico_mes, 0)
        }
    }


# -------------------------------------------------------------------
# GRÁFICOS (matplotlib → imagem em memória → ReportLab Image)
# -------------------------------------------------------------------

def _fig_to_image(fig, width_cm=18, height_cm=8):
    """Converte matplotlib Figure em ReportLab Image flowable."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    buf.seek(0)
    img = Image(buf, width=width_cm * cm, height=height_cm * cm)
    return img


def _gerar_grafico_barras(dados, meses, titulo="", cor="#E67E22", width_cm=18, height_cm=7):
    """Gráfico de barras mensal (geração anual)."""
    fig, ax = plt.subplots(figsize=(width_cm * 0.39, height_cm * 0.39))
    valores = [dados.get(m, 0) for m in meses]
    bars = ax.bar(meses, valores, color=cor, width=0.6, edgecolor='none')

    for bar, val in zip(bars, valores):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(valores) * 0.02,
                    f"{val:,.2f}".replace(",", "."), ha='center', va='bottom', fontsize=6, fontweight='bold')

    ax.set_ylim(0, max(valores) * 1.2 if max(valores) > 0 else 100)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(labelsize=7)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{x:,.2f}".replace(",", ".")))
    if titulo:
        ax.set_title(titulo, fontsize=9, fontweight='bold', pad=10)
    fig.tight_layout()
    return _fig_to_image(fig, width_cm, height_cm)


def _gerar_grafico_comparativo(dados_atual, dados_anterior, meses_label, mes_atual, mes_ant, width_cm=18, height_cm=7):
    """Gráfico de barras duplas (atual vs anterior) por dia."""
    dias = list(range(1, len(dados_atual) + 1))
    fig, ax = plt.subplots(figsize=(width_cm * 0.39, height_cm * 0.39))

    x_pos = range(len(dias))
    w = 0.35
    bars1 = ax.bar([p - w / 2 for p in x_pos], dados_atual, w, label=f"Atual ({mes_atual})", color="#B0BEC5")
    bars2 = ax.bar([p + w / 2 for p in x_pos], dados_anterior, w, label=f"Ant. ({mes_ant})", color="#E0E0E0")

    ax.set_xticks(x_pos)
    ax.set_xticklabels(dias, fontsize=5)
    ax.legend(fontsize=7, loc='upper right')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(labelsize=6)

    # Anotar valores relevantes
    for bar, val in zip(bars1, dados_atual):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{val:.2f}".replace(".", ","),
                    ha='center', va='bottom', fontsize=4, rotation=90)

    fig.tight_layout()
    return _fig_to_image(fig, width_cm, height_cm)


def _gerar_grafico_linhas(dados_dias, titulo="", cor="#27AE60", destaque=False, width_cm=18, height_cm=5.5):
    """Gráfico de linhas diário para um mês."""
    dias = list(range(1, len(dados_dias) + 1))
    fig, ax = plt.subplots(figsize=(width_cm * 0.39, height_cm * 0.39))

    ax.plot(dias, dados_dias, color=cor, marker='o', markersize=3, linewidth=1.5)

    # Anotar valores
    for d, val in zip(dias, dados_dias):
        if val > 0:
            ax.text(d, val + max(dados_dias) * 0.03, f"{val:,.2f}".replace(",", "."),
                    ha='center', va='bottom', fontsize=4.5)

    ax.set_xlim(0.5, 31.5)
    ax.set_xticks(range(1, 32, 2))
    ax.set_ylim(0, max(dados_dias) * 1.25 if max(dados_dias) > 0 else 100)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(labelsize=6)

    label = titulo
    if destaque:
        label += "  MELHOR MÊS"
    ax.set_title(label, fontsize=8, fontweight='bold', loc='left', pad=8, color=COR_AZUL_ESCURO)
    fig.tight_layout()
    return _fig_to_image(fig, width_cm, height_cm)


# -------------------------------------------------------------------
# SEÇÕES DO RELATÓRIO
# -------------------------------------------------------------------

def _criar_capa(story: list, dados: dict):
    """Página 1 — Capa com fundo escuro simulado e metadados."""
    meta = dados["METADADOS"]

    # Fundo simulado via tabela full-width com cor de fundo
    capa_data = [[""]]
    capa_tbl = Table(capa_data, colWidths=[PAGE_W - 40], rowHeights=[PAGE_H * 0.55])
    capa_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(COR_AZUL_ESCURO)),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(capa_tbl)

    # Título centralizado sobre o fundo
    s_titulo = ParagraphStyle('CapaTitulo', fontSize=30, fontName='Helvetica-Bold',
                              textColor=colors.white, alignment=TA_CENTER, spaceAfter=6)
    s_sub = ParagraphStyle('CapaSub', fontSize=14, fontName='Helvetica',
                           textColor=colors.white, alignment=TA_CENTER, spaceAfter=10)
    s_ano = ParagraphStyle('CapaAno', fontSize=24, fontName='Helvetica-Bold',
                           textColor=colors.HexColor(COR_DOURADO), alignment=TA_CENTER, spaceAfter=4)

    # Na verdade, precisamos inserir texto ANTES da tabela.
    # ReportLab não suporta overlay fácil, então vamos usar uma abordagem de
    # tabela com Paragraph dentro da célula.

    story.pop()  # remove a tabela vazia que acabamos de inserir

    inner_content = f"""
    <para alignment="center" spaceAfter="6">
    <font face="Helvetica-Bold" size="28" color="white">RELATÓRIO DE GESTÃO INTEGRADA</font>
    </para>
    """

    titulo_p = Paragraph(
        '<font face="Helvetica-Bold" size="28" color="white">RELATÓRIO DE GESTÃO INTEGRADA</font>',
        ParagraphStyle('t', alignment=TA_CENTER, leading=34)
    )
    sub_p = Paragraph(
        '<font face="Helvetica" size="14" color="white">PERFORMANCE OPERACIONAL</font>',
        ParagraphStyle('s', alignment=TA_CENTER, leading=20, spaceBefore=8)
    )
    ano_p = Paragraph(
        f'<font face="Helvetica-Bold" size="24" color="{COR_DOURADO}">{meta["ano"]}</font>',
        ParagraphStyle('a', alignment=TA_CENTER, leading=30, spaceBefore=10)
    )
    linha_dourada = HRFlowable(width="20%", thickness=3, color=colors.HexColor(COR_DOURADO),
                               spaceAfter=0, spaceBefore=6)

    # Bloco superior (fundo escuro simulado)
    bloco_capa = [[titulo_p], [sub_p], [ano_p], [linha_dourada]]
    tbl_capa = Table(bloco_capa, colWidths=[PAGE_W - 40], rowHeights=[50, 30, 40, 20])
    tbl_capa.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(COR_AZUL_ESCURO)),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 40),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(tbl_capa)

    story.append(Spacer(1, 10 * cm))

    # Metadados inferiores — grid 2x2
    lbl_style = ParagraphStyle('MetaLbl', fontSize=8, fontName='Helvetica',
                               textColor=colors.grey, spaceAfter=2, leading=10)
    val_style = ParagraphStyle('MetaVal', fontSize=11, fontName='Helvetica-Bold',
                               textColor=colors.HexColor(COR_AZUL_ESCURO), spaceAfter=2, leading=14)
    val_small = ParagraphStyle('MetaSmall', fontSize=9, fontName='Helvetica',
                               textColor=colors.HexColor(COR_LARANJA), leading=12)

    meta_grid = [
        [
            [Paragraph("CLIENTE PARCEIRO", lbl_style),
             Paragraph(meta["cliente"], val_style),
             Paragraph(meta["usina"], val_small)],
            [Paragraph("PERÍODO ANALISADO", lbl_style),
             Paragraph(meta["periodo"], val_style)]
        ],
        [
            [Paragraph("UNIDADE CONSUMIDORA", lbl_style),
             Paragraph(meta["unidade_consumidora"], val_style)],
            [Paragraph("EMISSÃO DO DOCUMENTO", lbl_style),
             Paragraph(meta["emissao"], val_style)]
        ]
    ]

    # Flatten: cada célula precisa ser um único flowable ou lista
    def _cell(items):
        from reportlab.platypus import Flowable
        # Retorna lista de paragraphs empilhados
        return items

    meta_table_data = []
    for row in meta_grid:
        table_row = []
        for cell_items in row:
            # Wrap em mini-tabela para empilhar
            mini = Table([[p] for p in cell_items], colWidths=[PAGE_W / 2 - 40])
            mini.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('TOPPADDING', (0, 0), (-1, -1), 1),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ]))
            table_row.append(mini)
        meta_table_data.append(table_row)

    meta_tbl = Table(meta_table_data, colWidths=[PAGE_W / 2 - 20, PAGE_W / 2 - 20],
                     rowHeights=[60, 50])
    meta_tbl.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEABOVE', (0, 0), (-1, 0), 0.5, colors.grey),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.grey),
        ('LINEBEFORE', (0, 0), (0, -1), 2, colors.HexColor(COR_DOURADO)),
    ]))
    story.append(meta_tbl)
    story.append(PageBreak())


def _criar_sumario(story: list, styles):
    """Página 2 — Sumário com itens pontilhados."""
    s_titulo = ParagraphStyle('SumTitulo', fontSize=24, fontName='Helvetica-Bold',
                              textColor=colors.HexColor(COR_AZUL_ESCURO), spaceAfter=4, leading=30)
    story.append(Paragraph("Sumário", s_titulo))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor(COR_AZUL_ESCURO),
                             spaceAfter=20, spaceBefore=4))

    itens = [
        ("1. CAPA", "1"),
        ("2. SUMÁRIO", "2"),
        ("3. TABELA DE GERAÇÃO OPERACIONAL (MWH)", "3"),
        ("4. ANÁLISE DE PERFORMANCE OPERACIONAL (GRÁFICOS)", "4"),
        ("5. CURVAS DE GERAÇÃO DIÁRIA POR MÊS", "5"),
    ]

    s_item = ParagraphStyle('SumItem', fontSize=11, fontName='Helvetica-Bold',
                            textColor=colors.HexColor(COR_AZUL_ESCURO), leading=16)
    s_dots = ParagraphStyle('SumDots', fontSize=11, fontName='Helvetica',
                            textColor=colors.grey, leading=16, alignment=TA_RIGHT)

    for titulo, pag in itens:
        # Criar tabela com 2 colunas: título + página com pontos
        dots = "·" * 80
        row_data = [
            [Paragraph(titulo, s_item),
             Paragraph(pag, ParagraphStyle('pg', fontSize=11, alignment=TA_RIGHT,
                                           textColor=colors.HexColor(COR_AZUL_ESCURO)))]
        ]
        row_tbl = Table(row_data, colWidths=[PAGE_W - 80, 30])
        row_tbl.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, 0), 0.3, colors.lightgrey),
        ]))
        story.append(row_tbl)
        story.append(Spacer(1, 0.3 * cm))

    story.append(PageBreak())


def _criar_tabela_geracao(story: list, dados: dict):
    """Página 3 — Tabela completa com 12 meses, valor+%, totais e rodapé."""
    meta = dados["METADADOS"]
    s_titulo = ParagraphStyle('TblTitulo', fontSize=16, fontName='Helvetica-Bold',
                              textColor=colors.HexColor(COR_AZUL_ESCURO), spaceAfter=10, leading=20)
    story.append(Paragraph(f"ANEXO I - GERAÇÃO OPERACIONAL ({meta['ano']})", s_titulo))

    meses = dados["MESES_TODOS"]
    gf_mensal = dados["GF_MENSAL"]

    # Estilos para célula com 2 linhas (valor + %)
    s_val = '<font face="Helvetica-Bold" size="7">%s</font>'
    s_pct = '<font face="Helvetica" size="5" color="#999999">%s</font>'
    s_header = '<font face="Helvetica-Bold" size="7" color="%s">%s</font>'

    # Cabeçalho
    header = [Paragraph(s_header % (COR_AZUL_ESCURO, "DIA"), ParagraphStyle('h', alignment=TA_CENTER, leading=10))]
    for m in meses:
        header.append(Paragraph(s_header % (COR_LARANJA, m), ParagraphStyle('h', alignment=TA_CENTER, leading=10)))
    table_data = [header]

    # Linhas de dados (31 dias)
    for dia in range(1, 32):
        row = [Paragraph(f'<font face="Helvetica" size="7">{dia}º</font>',
                         ParagraphStyle('d', alignment=TA_CENTER, leading=10))]
        for mes in meses:
            valor = dados["GERACAO_DIARIA"][mes][dia - 1]
            if valor > 0:
                pct = valor / (gf_mensal[mes] / 31) * 100  # % da GF diária
                cell_text = f'{s_val % f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")}<br/>{s_pct % f"{pct:.1f}%"}'
            else:
                cell_text = ""
            row.append(Paragraph(cell_text, ParagraphStyle('c', alignment=TA_CENTER, leading=8)))
        table_data.append(row)

    # Linha TOTAL
    row_total = [Paragraph(s_val % "TOTAL", ParagraphStyle('t', alignment=TA_CENTER, leading=10))]
    for m in meses:
        v = dados["TOTAIS_MES"][m]
        txt = f'<font face="Helvetica-Bold" size="7" color="white">{v:,.2f}</font>'.replace(",", "X").replace(".", ",").replace("X", ".")
        row_total.append(Paragraph(txt, ParagraphStyle('tv', alignment=TA_CENTER, leading=10)))
    table_data.append(row_total)

    # Linha G. FÍSICA
    row_gf = [Paragraph(s_val % "G. FÍSICA", ParagraphStyle('t', alignment=TA_CENTER, leading=10))]
    for m in meses:
        v = gf_mensal[m]
        txt = f'<font face="Helvetica-Bold" size="7">{v:,.2f}</font>'.replace(",", "X").replace(".", ",").replace("X", ".")
        row_gf.append(Paragraph(txt, ParagraphStyle('gv', alignment=TA_CENTER, leading=10)))
    table_data.append(row_gf)

    # Linha PERF. %
    row_perf = [Paragraph(s_val % "PERF. %", ParagraphStyle('t', alignment=TA_CENTER, leading=10))]
    for m in meses:
        p = dados["PERF_MES"][m]
        txt = f'<font face="Helvetica-Bold" size="7">{p}</font>'
        row_perf.append(Paragraph(txt, ParagraphStyle('pv', alignment=TA_CENTER, leading=10)))
    table_data.append(row_perf)

    # Construir tabela
    col_dia = 1.2 * cm
    col_mes = (PAGE_W - 40 - col_dia) / 12
    tabela = Table(table_data, colWidths=[col_dia] + [col_mes] * 12)

    estilo = TableStyle([
        # Cabeçalho
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(COR_FUNDO_HEADER)),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 1),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.Color(0.85, 0.85, 0.85)),
        # TOTAL (linha -3)
        ('BACKGROUND', (0, -3), (-1, -3), colors.HexColor(COR_AZUL_ESCURO)),
        ('TEXTCOLOR', (0, -3), (-1, -3), colors.white),
        # G. FÍSICA e PERF
        ('BACKGROUND', (0, -2), (-1, -1), colors.HexColor(COR_CINZA_CLARO)),
    ])

    # Zebra nas linhas de dados
    for i in range(1, 32):
        bg = colors.HexColor(COR_FUNDO_HEADER) if i % 2 != 0 else colors.white
        estilo.add('BACKGROUND', (0, i), (-1, i), bg)

    tabela.setStyle(estilo)
    story.append(tabela)
    story.append(Spacer(1, 0.4 * cm))

    # Rodapé da tabela — legenda e resumo
    resumo = dados["RESUMO"]
    meta_d = dados["METADADOS"]

    s_leg = ParagraphStyle('Leg', fontSize=8, leading=12)
    legenda_items = [
        [Paragraph(f'<font color="white">██</font> Meta Atingida ({meta_d["meta_dia_mw"]} MW/dia)', s_leg),
         Paragraph(f'<font color="{COR_LARANJA}">██</font> Abaixo da Meta', s_leg),
         Paragraph(f'GF Anual: <b>{resumo["gf_anual"]:,.2f} MW</b>'.replace(",", "."), s_leg),
         Paragraph(f'Geração Anual: <b><font color="blue">{resumo["geracao_anual"]:,.2f} MW</font></b>'.replace(",", "."), s_leg),
         Paragraph(f'Perf. Global: <b><font color="red">{resumo["perf_global"]}</font></b>', s_leg)]
    ]
    leg_tbl = Table(legenda_items, colWidths=[(PAGE_W - 40) / 5] * 5)
    leg_tbl.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(leg_tbl)

    story.append(Spacer(1, 0.2 * cm))
    s_gf = ParagraphStyle('GF', fontSize=9, leading=12, textColor=colors.HexColor(COR_AZUL_ESCURO))
    story.append(Paragraph(
        f'Garantia Física (GF): <font color="blue"><b>{meta_d["gf_mwh"]} MWh</b></font>', s_gf))

    # Rodapé seção
    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceAfter=4))
    s_rodape = ParagraphStyle('Rodape', fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    story.append(Paragraph("Seção 3 - Tabela de Geração e Performance Diária (MWh)", s_rodape))
    story.append(PageBreak())


def _criar_pagina_performance(story: list, dados: dict):
    """Página 4 — Análise de performance com gráficos de barras."""
    s_titulo = ParagraphStyle('PerfTit', fontSize=20, fontName='Helvetica-Bold',
                              textColor=colors.HexColor(COR_AZUL_ESCURO), spaceAfter=4, leading=24)
    s_sub = ParagraphStyle('PerfSub', fontSize=10, textColor=colors.grey, spaceAfter=10)

    story.append(Paragraph("ANÁLISE DE PERFORMANCE OPERACIONAL", s_titulo))
    story.append(Paragraph(f"Comparativo e Histórico do Ano {dados['METADADOS']['ano']}", s_sub))

    # Cards de resumo
    resumo = dados["RESUMO"]
    s_card_lbl = ParagraphStyle('CardLbl', fontSize=8, textColor=colors.grey, leading=10)
    s_card_val = ParagraphStyle('CardVal', fontSize=14, fontName='Helvetica-Bold',
                                textColor=colors.HexColor(COR_AZUL_ESCURO), leading=18)
    s_card_small = ParagraphStyle('CardSmall', fontSize=8, textColor=colors.grey, leading=10)

    cards_data = [[
        [Paragraph("GERAÇÃO TOTAL ANUAL", s_card_lbl),
         Paragraph(f'{resumo["geracao_anual"]:,.2f} MWh'.replace(",", "."), s_card_val)],
        [Paragraph("MÉDIA DE GERAÇÃO MENSAL", s_card_lbl),
         Paragraph(f'{resumo["media_mensal"]:,.2f} MWh/mês'.replace(",", "."), s_card_val)],
        [Paragraph("PICO DE GERAÇÃO", s_card_lbl),
         Paragraph(f'{resumo["pico_mes"]} ({resumo["pico_valor"]:,.2f})'.replace(",", "."), s_card_val)],
    ]]

    # Flatten para tabela
    card_row = []
    for cell_items in cards_data[0]:
        mini = Table([[p] for p in cell_items], colWidths=[(PAGE_W - 60) / 3])
        mini.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8F9FA")),
        ]))
        card_row.append(mini)

    cards_tbl = Table([card_row], colWidths=[(PAGE_W - 60) / 3] * 3)
    cards_tbl.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(cards_tbl)
    story.append(Spacer(1, 0.5 * cm))

    # Gráfico 1: Barras anual
    s_graf = ParagraphStyle('GrafTit', fontSize=10, fontName='Helvetica-Bold',
                            textColor=colors.HexColor(COR_AZUL_ESCURO), spaceAfter=4)
    story.append(Paragraph("COMPARATIVO ANUAL (GERAÇÃO MWH)", s_graf))
    img_barras = _gerar_grafico_barras(dados["TOTAIS_MES"], MESES_TODOS, cor=COR_LARANJA)
    story.append(img_barras)
    story.append(Spacer(1, 0.5 * cm))

    # Gráfico 2: Comparativo diário último mês vs anterior
    meses_op = dados["MESES_OPERADOS"]
    if len(meses_op) >= 2:
        mes_atual = meses_op[-1]
        mes_ant = meses_op[-2]
        story.append(Paragraph(f"COMPARATIVO DIÁRIO ({mes_atual} VS {mes_ant}) - GERAÇÃO (MWH)", s_graf))
        img_comp = _gerar_grafico_comparativo(
            dados["GERACAO_DIARIA"][mes_atual],
            dados["GERACAO_DIARIA"][mes_ant],
            list(range(1, 32)),
            mes_atual, mes_ant
        )
        story.append(img_comp)

    # Rodapé seção
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceAfter=4))
    s_rodape = ParagraphStyle('Rodape', fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    story.append(Paragraph("Seção 4 - Gráficos e Desempenho Operacional", s_rodape))
    story.append(PageBreak())


def _criar_curvas_diarias(story: list, dados: dict):
    """Páginas 5+ — Gráficos de linha por mês operado."""
    meses_op = dados["MESES_OPERADOS"]
    resumo = dados["RESUMO"]
    pico_mes = resumo["pico_mes"]

    s_titulo = ParagraphStyle('CurvTit', fontSize=20, fontName='Helvetica-Bold',
                              textColor=colors.HexColor(COR_AZUL_ESCURO), spaceAfter=4, leading=24)
    s_sub = ParagraphStyle('CurvSub', fontSize=10, textColor=colors.grey, spaceAfter=10)

    # Agrupar 3 gráficos por página
    graficos_por_pagina = 3
    for idx, mes in enumerate(meses_op):
        if idx % graficos_por_pagina == 0:
            if idx > 0:
                # Rodapé da página anterior
                part = f"({idx // graficos_por_pagina}/{-(-len(meses_op) // graficos_por_pagina)})"
                story.append(Spacer(1, 0.3 * cm))
                story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceAfter=4))
                s_rodape = ParagraphStyle('Rodape', fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
                story.append(Paragraph(f"Seção 5 - Detalhamento Diário {part}", s_rodape))
                story.append(PageBreak())
            story.append(Paragraph("CURVAS DE GERAÇÃO DIÁRIA", s_titulo))
            story.append(Paragraph("Detalhamento dia a dia dos meses operados", s_sub))

        titulo_graf = f"GERAÇÃO DE {mes} {dados['METADADOS']['ano']} (MWH)"
        destaque = (mes == pico_mes)
        img = _gerar_grafico_linhas(dados["GERACAO_DIARIA"][mes], titulo_graf, cor=COR_VERDE, destaque=destaque)
        story.append(img)
        story.append(Spacer(1, 0.3 * cm))

    # Rodapé última página
    total_pages = -(-len(meses_op) // graficos_por_pagina)
    current = total_pages
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey, spaceAfter=4))
    s_rodape = ParagraphStyle('Rodape', fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    story.append(Paragraph(f"Seção 5 - Detalhamento Diário ({current}/{total_pages})", s_rodape))


# -------------------------------------------------------------------
# ORQUESTRADOR
# -------------------------------------------------------------------

@desempenho
def gerar_relatorio(pdf_filename: str, dados: dict = None):
    """Gera o PDF completo com todas as seções."""
    if dados is None:
        dados = _get_mock_data()

    doc = SimpleDocTemplate(
        pdf_filename, pagesize=A4,
        rightMargin=20, leftMargin=20,
        topMargin=30, bottomMargin=30
    )
    styles = getSampleStyleSheet()
    story = []

    _criar_capa(story, dados)
    _criar_sumario(story, styles)
    _criar_tabela_geracao(story, dados)
    _criar_pagina_performance(story, dados)
    _criar_curvas_diarias(story, dados)

    doc.build(story)
    return pdf_filename


# -------------------------------------------------------------------
# EXECUÇÃO
# -------------------------------------------------------------------
if __name__ == "__main__":
    path = gerar_relatorio(ARQUIVO_SAIDA)
    print(f"PDF gerado: {path}")