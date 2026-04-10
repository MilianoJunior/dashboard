# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. home          -> Retorna shell com loading overlay (resposta rápida)
# 2. api_dashboard -> Retorna seções renderizadas via AJAX (dados pesados)
# 3. health        -> Endpoint simples de saúde da aplicação
# -------------------------------------------------------------------

from flask import Blueprint, jsonify, render_template, request

from libs.controllers.dashboard_controller import (
    get_dashboard_data,
    USINAS_DISPONIVEIS,
    USINA_PADRAO,
)
from libs.utils.decorators import desempenho

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@desempenho
def home():
    """Shell leve — dados pesados carregam via /api/dashboard."""
    codigo_usina = request.args.get("usina", USINA_PADRAO)
    if codigo_usina not in USINAS_DISPONIVEIS:
        codigo_usina = USINA_PADRAO

    return render_template(
        "componentes/dashboard.html",
        codigo_usina=codigo_usina,
        usinas_disponiveis=USINAS_DISPONIVEIS,
    )


@dashboard_bp.route("/api/dashboard")
@desempenho
def api_dashboard():
    """Processa dados pesados e retorna HTML pré-renderizado por seção."""
    data = get_dashboard_data(request.args)
    return jsonify({
        "gauge_grid": render_template("componentes/gauge_grid.html", **data),
        "generation_chart": render_template("componentes/generation_chart.html", **data),
        "reservoir_chart": render_template("componentes/reservoir_chart.html", **data),
    })


@dashboard_bp.route("/health")
@desempenho
def health():
    return jsonify({"status": "ok"}), 200
