# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. _preparar_dados_geracao -> Consulta e normaliza produção para o template
# 2. _preparar_dados_nivel   -> Consulta e normaliza níveis para o template
# 3. _parse_filtros          -> Lê filtros da query string
# 4. get_dashboard_data      -> Monta o contexto completo do dashboard
# 5. home                    -> Renderiza a rota principal do Flask
# -------------------------------------------------------------------

import re
import os
from datetime import datetime, timedelta

from flask import Flask, render_template, request

from libs.controllers.consultas import (
    consultar_producao,
    consultar_nivel,
    normalizar_energia,
    normalizar_nivel,
    carregar_config_usina,
)

from libs.utils.decorators import desempenho

app = Flask(
    __name__,
    template_folder='libs/views',
    static_folder='assets',
)

# Paleta de cores pastel padrão por UG — consistente em gauges, gráficos e legendas
UG_COLORS = [
    '#5BC0EB',  # UG-01 — azul pastel
    '#9B5DE5',  # UG-02 — roxo pastel
    '#F15BB5',  # UG-03 — rosa pastel
    '#FEE440',  # UG-04 — amarelo pastel
    '#00F5D4',  # UG-05 — verde-água pastel
]

# Cores para linhas de nível
NIVEL_COLORS = ['#02aeef', '#a4a1ff', '#c4d7e5', '#70767e', '#f9a825', '#ef5350']

# Mapa período UI -> código API
PERIODOS = {
    'HORA':    {'api': 'H', 'delta_days': 1,   'fmt_label': '%H:%M'},
    'DIÁRIO':  {'api': 'D', 'delta_days': 30,  'fmt_label': '%d/%m'},
    'MENSAL':  {'api': 'M', 'delta_days': 365, 'fmt_label': '%m/%Y'},
}

USINAS = ['PCH-PIRA', 'PCH-PEDRAS','CGH-APARECIDA','CGH-PICADAS-ALTAS','CGH-FAE','CGH-HOPPEN'][0]
    

@desempenho
def _preparar_dados_geracao(codigo_usina=USINAS, periodo="DIÁRIO",
                            data_inicio=None, data_fim=None):
    """Consulta e normaliza produção por período."""
    cfg = PERIODOS[periodo]
    periodo_api = cfg['api']
    fmt_label = cfg['fmt_label']

    resposta = consultar_producao(
        periodo=periodo_api,
        data_inicio=data_inicio,
        data_fim=data_fim,
        codigo_usina=codigo_usina,
    )
    df = normalizar_energia(resposta, periodo=periodo_api)

    if df.empty:
        return [], []

    # Extrair nome curto das UGs: "UG-01 Energia Acumulada" -> "UG-01"
    ug_names = []
    for col in df.columns:
        match = re.search(r'(UG-\d+)', col)
        ug_names.append(match.group(1) if match else col)

    chart_data = []
    for dt_index, row in df.iterrows():
        values = [float(row[col]) for col in df.columns]
        total = sum(values)
        chart_data.append({
            'day_label': dt_index.strftime(fmt_label),
            'ug_values': values,
            'total': round(total, 2),
        })

    return chart_data, ug_names

@desempenho
def _preparar_dados_nivel(codigo_usina=USINAS, data_inicio=None, data_fim=None):
    """Consulta nível hidráulico e prepara dados para o gráfico de linhas SVG."""
    config = carregar_config_usina(codigo_usina)
    nivel_vertimento = config.get('nivel_vertimento', 100.0)

    resposta = consultar_nivel(codigo_usina=codigo_usina, data_inicio=data_inicio, data_fim=data_fim)
    df = normalizar_nivel(resposta)

    if df.empty:
        return {
            'nivel_series': [],
            'nivel_labels': [],
            'nivel_vertimento': nivel_vertimento,
            'nivel_colors': [],
        }

    col_names = list(df.columns)

    # Calcular range Y baseado nos dados reais
    all_values = df[col_names].values.flatten()
    y_min = float(all_values.min())
    y_max = float(all_values.max())
    y_max = max(y_max, nivel_vertimento)
    margem = (y_max - y_min) * 0.1 if y_max != y_min else 1.0
    y_bottom = y_min - margem
    y_top = y_max + margem
    y_range = y_top - y_bottom

    # Gerar SVG paths para cada coluna de nível
    svg_w, svg_h = 1000, 250
    n_points = len(df)

    nivel_series = []
    for i, col in enumerate(col_names):
        points = []
        for j, (dt_idx, val) in enumerate(df[col].items()):
            x = (j / max(n_points - 1, 1)) * svg_w
            y = svg_h - ((float(val) - y_bottom) / y_range * svg_h)
            points.append(f"{x:.1f},{y:.1f}")

        # Construir path SVG com linhas
        if points:
            path = "M" + " L".join(points)
        else:
            path = ""

        nivel_series.append({
            'name': col,
            'path': path,
            'color': NIVEL_COLORS[i % len(NIVEL_COLORS)],
        })

    # Posição Y do nível de vertimento no SVG
    spill_y = svg_h - ((nivel_vertimento - y_bottom) / y_range * svg_h)

    # Labels do eixo X (timestamps espaçados)
    indices = df.index
    n_labels = min(7, len(indices))
    step = max(len(indices) // n_labels, 1)
    time_labels = []
    for k in range(0, len(indices), step):
        time_labels.append(indices[k].strftime('%d/%m %H:%M'))
    # Garantir último
    if time_labels and indices[-1].strftime('%d/%m %H:%M') != time_labels[-1]:
        time_labels.append(indices[-1].strftime('%d/%m %H:%M'))

    # Labels do eixo Y
    y_axis_labels = []
    for frac in [1.0, 0.75, 0.5, 0.25, 0.0]:
        val = y_bottom + frac * y_range
        y_axis_labels.append(f"{val:.1f}m")

    return {
        'nivel_series': nivel_series,
        'nivel_labels': time_labels,
        'nivel_vertimento': nivel_vertimento,
        'nivel_vertimento_label': f"{nivel_vertimento:.2f}m",
        'spill_y': round(spill_y, 1),
        'nivel_colors': NIVEL_COLORS,
        'nivel_y_axis': y_axis_labels,
    }

@desempenho
def _parse_filtros():
    """Lê parâmetros de filtro da query string."""
    periodo = request.args.get('periodo', 'DIÁRIO')
    if periodo not in PERIODOS:
        periodo = 'DIÁRIO'

    agora = datetime.now()
    delta = timedelta(days=PERIODOS[periodo]['delta_days'])

    start_str = request.args.get('start_date', '')
    end_str = request.args.get('end_date', '')

    try:
        data_inicio = datetime.strptime(start_str, '%Y-%m-%d')
    except ValueError:
        data_inicio = agora - delta

    try:
        data_fim = datetime.strptime(end_str, '%Y-%m-%d')
    except ValueError:
        data_fim = agora

    return periodo, data_inicio, data_fim


@desempenho
def get_dashboard_data():
    """Monta dados do dashboard combinando dados reais da API com mock."""
    periodo, data_inicio, data_fim = _parse_filtros()
    codigo_usina = USINAS

    # Gauges (mock por enquanto)
    usinas = [
        {'name': 'UG-01', 'status': 'Ativa', 'percent': 82, 'power_mw': 45.2, 'variant': 'normal', 'color': UG_COLORS[0]},
        {'name': 'UG-02', 'status': 'Ativa', 'percent': 89, 'power_mw': 48.9, 'variant': 'normal', 'color': UG_COLORS[1]},
        {'name': 'UG-03', 'status': 'Atenção', 'percent': 96, 'power_mw': 52.8, 'variant': 'warning', 'color': UG_COLORS[2]},
        {'name': 'UG-04', 'status': 'Crítico', 'percent': 100, 'power_mw': 55.0, 'variant': 'critical', 'color': UG_COLORS[3]},
        {'name': 'UG-05', 'status': 'Ativa', 'percent': 58, 'power_mw': 31.9, 'variant': 'normal', 'color': UG_COLORS[4]},
    ]

    # Geração — dados reais da API com período dinâmico
    chart_data, ug_names = _preparar_dados_geracao(
        codigo_usina=codigo_usina,
        periodo=periodo,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    max_total = max((d['total'] for d in chart_data), default=100)

    # Nível dos reservatórios — dados reais da API
    nivel_data = _preparar_dados_nivel(
        codigo_usina=codigo_usina,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    

    return {
        'usinas': usinas,
        'chart_data': chart_data,
        'ug_names': ug_names,
        'ug_colors': UG_COLORS,
        'unit_count': len(ug_names) or 5,
        'max_total': max_total,
        'start_date': data_inicio.strftime('%Y-%m-%d'),
        'end_date': data_fim.strftime('%Y-%m-%d'),
        'active_period': periodo,
        'codigo_usina': codigo_usina,
        **nivel_data,
    }


@app.route('/')
@desempenho
def home():
    data = get_dashboard_data()
    return render_template('componentes/dashboard.html', **data)


if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    app.run(debug=debug, host='0.0.0.0', port=port)
