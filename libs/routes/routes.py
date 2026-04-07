# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. home   -> Renderiza o dashboard principal
# 2. health -> Endpoint simples de saúde da aplicação
# -------------------------------------------------------------------

from flask import Blueprint, jsonify, render_template, request

from libs.controllers.dashboard_controller import get_dashboard_data
from libs.utils.decorators import desempenho

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@desempenho
def home():
    data = get_dashboard_data(request.args)
    return render_template("componentes/dashboard.html", **data)


@dashboard_bp.route("/health")
@desempenho
def health():
    return jsonify({"status": "ok"}), 200
