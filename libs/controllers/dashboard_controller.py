# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. _parse_filtros          -> Lê filtros da query string
# 2. _preparar_dados_geracao -> Consulta e normaliza produção para o template
# 3. _preparar_dados_nivel   -> Consulta e normaliza níveis para o template
# 4. get_dashboard_data      -> Monta o contexto completo do dashboard
# -------------------------------------------------------------------

import re
from datetime import datetime, timedelta

from libs.models.gauge_rt import dispositivo_tem_gauge
from libs.models.consultas import (
    carregar_config_usina,
    consultar_nivel,
    consultar_producao,
    normalizar_energia,
    normalizar_nivel,
)
from libs.utils.decorators import desempenho

UG_COLORS = [
    "#5BC0EB",
    "#9B5DE5",
    "#F15BB5",
    "#FEE440",
    "#00F5D4",
]

NIVEL_COLORS = ["#02aeef", "#a4a1ff", "#c4d7e5", "#70767e", "#f9a825", "#ef5350"]

PERIODOS = {
    "HORA": {"api": "H", "delta_days": 1, "fmt_label": "%H:%M"},
    "DIÁRIO": {"api": "D", "delta_days": 30, "fmt_label": "%d/%m"},
    "MENSAL": {"api": "M", "delta_days": 365, "fmt_label": "%m/%Y"},
}

USINAS_DISPONIVEIS = [
    "PCH-PIRA",
    "PCH-PEDRAS",
    "CGH-APARECIDA",
    "CGH-PICADAS-ALTAS",
    "CGH-FAE",
    "CGH-HOPPEN",
]

USINA_PADRAO = USINAS_DISPONIVEIS[0]


def _montar_gauges_iniciais(codigo_usina):
    """Monta lista de gauges com valores zerados a partir do config.
    Os valores reais são atualizados via WebSocket.
    """
    config = carregar_config_usina(codigo_usina)
    dispositivos = config.get("dispositivos", {})

    usinas = []
    idx = 0
    for nome_disp, disp_cfg in dispositivos.items():
        if not dispositivo_tem_gauge(disp_cfg):
            continue
        pot_max = disp_cfg.get("caracteristicas", {}).get("potência máxima", 0)
        usinas.append({
            "name": nome_disp,
            "status": "Carregando...",
            "percent": 0,
            "power_kw": 0,
            "pot_max_kw": pot_max,
            "variant": "normal",
            "color": UG_COLORS[idx % len(UG_COLORS)],
        })
        idx += 1

    return usinas


def _montar_resumo_rt_inicial(codigo_usina):
    config = carregar_config_usina(codigo_usina)
    dispositivos = config.get("dispositivos", {})

    pot_max_total_kw = 0.0
    for disp_cfg in dispositivos.values():
        if not dispositivo_tem_gauge(disp_cfg):
            continue
        pot_max_total_kw += float(disp_cfg.get("caracteristicas", {}).get("potência máxima", 0) or 0)

    return {
        "nivel_montante": None,
        "total_power_kw": 0.0,
        "percent_total": 0,
        "pot_max_total_kw": round(pot_max_total_kw, 1),
    }


@desempenho
def _parse_filtros(parametros=None):
    parametros = parametros or {}

    periodo = parametros.get("periodo", "DIÁRIO")
    if periodo not in PERIODOS:
        periodo = "DIÁRIO"

    agora = datetime.now()
    delta = timedelta(days=PERIODOS[periodo]["delta_days"])

    start_str = parametros.get("start_date", "")
    end_str = parametros.get("end_date", "")

    try:
        data_inicio = datetime.strptime(start_str, "%Y-%m-%d")
    except ValueError:
        data_inicio = agora - delta

    try:
        data_fim = datetime.strptime(end_str, "%Y-%m-%d")
    except ValueError:
        data_fim = agora

    return periodo, data_inicio, data_fim


@desempenho
def _preparar_dados_geracao(codigo_usina=USINA_PADRAO, periodo="DIÁRIO", data_inicio=None, data_fim=None):
    cfg = PERIODOS[periodo]
    periodo_api = cfg["api"]
    fmt_label = cfg["fmt_label"]

    resposta = consultar_producao(
        periodo=periodo_api,
        data_inicio=data_inicio,
        data_fim=data_fim,
        codigo_usina=codigo_usina,
    )
    df = normalizar_energia(resposta, periodo=periodo_api)

    if df.empty:
        return [], []

    ug_names = []
    for col in df.columns:
        match = re.search(r"(UG-\d+)", col)
        ug_names.append(match.group(1) if match else col)

    chart_data = []
    for dt_index, row in df.iterrows():
        values = [float(row[col]) for col in df.columns]
        total = sum(values)
        chart_data.append(
            {
                "day_label": dt_index.strftime(fmt_label),
                "ug_values": values,
                "total": round(total, 2),
            }
        )

    return chart_data, ug_names


@desempenho
def _preparar_dados_nivel(codigo_usina=USINA_PADRAO, data_inicio=None, data_fim=None):
    config = carregar_config_usina(codigo_usina)
    nivel_vertimento = config.get("nivel_vertimento", 100.0)

    resposta = consultar_nivel(
        codigo_usina=codigo_usina,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )
    df = normalizar_nivel(resposta)

    if df.empty:
        return {
            "nivel_series": [],
            "nivel_labels": [],
            "nivel_vertimento": nivel_vertimento,
            "nivel_colors": [],
        }

    col_names = list(df.columns)

    all_values = df[col_names].values.flatten()
    y_min = float(all_values.min())
    y_max = float(all_values.max())
    y_max = max(y_max, nivel_vertimento)
    margem = (y_max - y_min) * 0.1 if y_max != y_min else 1.0
    y_bottom = y_min - margem
    y_top = y_max + margem
    y_range = y_top - y_bottom

    svg_w, svg_h = 1000, 250
    n_points = len(df)

    nivel_series = []
    for indice, coluna in enumerate(col_names):
        points = []
        for posicao, (_, valor) in enumerate(df[coluna].items()):
            x = (posicao / max(n_points - 1, 1)) * svg_w
            y = svg_h - ((float(valor) - y_bottom) / y_range * svg_h)
            points.append(f"{x:.1f},{y:.1f}")

        nivel_series.append(
            {
                "name": coluna,
                "path": "M" + " L".join(points) if points else "",
                "color": NIVEL_COLORS[indice % len(NIVEL_COLORS)],
            }
        )

    spill_y = svg_h - ((nivel_vertimento - y_bottom) / y_range * svg_h)

    indices = df.index
    quantidade_labels = min(7, len(indices))
    step = max(len(indices) // quantidade_labels, 1)
    time_labels = []
    for indice in range(0, len(indices), step):
        time_labels.append(indices[indice].strftime("%d/%m %H:%M"))
    if time_labels and indices[-1].strftime("%d/%m %H:%M") != time_labels[-1]:
        time_labels.append(indices[-1].strftime("%d/%m %H:%M"))

    y_axis_labels = []
    for frac in [1.0, 0.75, 0.5, 0.25, 0.0]:
        valor = y_bottom + frac * y_range
        y_axis_labels.append(f"{valor:.1f}m")

    return {
        "nivel_series": nivel_series,
        "nivel_labels": time_labels,
        "nivel_vertimento": nivel_vertimento,
        "nivel_vertimento_label": f"{nivel_vertimento:.2f}m",
        "spill_y": round(spill_y, 1),
        "nivel_colors": NIVEL_COLORS,
        "nivel_y_axis": y_axis_labels,
    }


@desempenho
def get_dashboard_data(parametros=None):
    periodo, data_inicio, data_fim = _parse_filtros(parametros)
    parametros = parametros or {}
    codigo_usina = parametros.get("usina", USINA_PADRAO)
    if codigo_usina not in USINAS_DISPONIVEIS:
        codigo_usina = USINA_PADRAO

    # Dados iniciais dos gauges (placeholder — dados reais chegam via WebSocket)
    usinas = _montar_gauges_iniciais(codigo_usina)
    resumo_rt = _montar_resumo_rt_inicial(codigo_usina)

    chart_data, ug_names = _preparar_dados_geracao(
        codigo_usina=codigo_usina,
        periodo=periodo,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    max_total = max((dado["total"] for dado in chart_data), default=100)

    nivel_data = _preparar_dados_nivel(
        codigo_usina=codigo_usina,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    return {
        "usinas": usinas,
        "chart_data": chart_data,
        "ug_names": ug_names,
        "ug_colors": UG_COLORS,
        "unit_count": len(ug_names) or 5,
        "max_total": max_total,
        "start_date": data_inicio.strftime("%Y-%m-%d"),
        "end_date": data_fim.strftime("%Y-%m-%d"),
        "active_period": periodo,
        "codigo_usina": codigo_usina,
        "usinas_disponiveis": USINAS_DISPONIVEIS,
        "resumo_rt": resumo_rt,
        **nivel_data,
    }
