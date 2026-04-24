# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. login         -> GET exibe formulário; POST valida contra usuarios.json
# 2. logout        -> Encerra sessão e redireciona ao login
# 3. home          -> Shell protegido, usina vem da sessão
# 4. api_dashboard -> Retorna seções renderizadas via AJAX (dados pesados)
# 5. reports       -> Tela protegida para geracao de relatorios PDF
# 6. reports_pdf   -> Gera PDF premium com dados historicos da API
# 7. health        -> Endpoint simples de saúde da aplicação
# -------------------------------------------------------------------

from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from libs.controllers.dashboard_controller import (
    get_dashboard_data,
    USINAS_DISPONIVEIS,
    USINA_PADRAO,
)
from libs.utils.auth import autenticar, login_required
from libs.utils.decorators import desempenho
from libs.controllers.reports_controller import (
    gerar_pdf_relatorio,
    listar_anos_relatorio,
    parse_report_params,
)

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/login", methods=["GET", "POST"])
def login():
    erro = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        usina = autenticar(username, password)
        if usina and usina in USINAS_DISPONIVEIS:
            session["username"] = username.strip()
            session["codigo_usina"] = usina
            return redirect(url_for("dashboard.home"))
        erro = "Usuário ou senha inválidos."
    return render_template("componentes/login.html", erro=erro)


@dashboard_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("dashboard.login"))


@dashboard_bp.route("/")
@login_required
@desempenho
def home():
    """Shell leve — dados pesados carregam via /api/dashboard."""
    codigo_usina = session.get("codigo_usina", USINA_PADRAO)
    if codigo_usina not in USINAS_DISPONIVEIS:
        codigo_usina = USINA_PADRAO

    return render_template(
        "componentes/dashboard.html",
        codigo_usina=codigo_usina,
        username=session.get("username", ""),
        active_page="dashboard",
    )


@dashboard_bp.route("/api/dashboard")
@login_required
@desempenho
def api_dashboard():
    """Processa dados pesados e retorna HTML pré-renderizado por seção."""
    args = request.args.to_dict()
    args["usina"] = session.get("codigo_usina", USINA_PADRAO)
    data = get_dashboard_data(args)
    return jsonify({
        "gauge_grid": render_template("componentes/gauge_grid.html", **data),
        "generation_chart": render_template("componentes/generation_chart.html", **data),
        "reservoir_chart": render_template("componentes/reservoir_chart.html", **data),
    })


@dashboard_bp.route("/reports")
@login_required
@desempenho
def reports():
    codigo_usina = session.get("codigo_usina", USINA_PADRAO)
    if codigo_usina not in USINAS_DISPONIVEIS:
        codigo_usina = USINA_PADRAO

    filtros = parse_report_params(request.args)
    return render_template(
        "componentes/reports.html",
        codigo_usina=codigo_usina,
        username=session.get("username", ""),
        active_page="reports",
        anos_relatorio=listar_anos_relatorio(),
        ano_selecionado=filtros["ano"],
    )


@dashboard_bp.route("/reports/pdf", methods=["POST"])
@login_required
@desempenho
def reports_pdf():
    codigo_usina = session.get("codigo_usina", USINA_PADRAO)
    if codigo_usina not in USINAS_DISPONIVEIS:
        codigo_usina = USINA_PADRAO

    filtros = parse_report_params(request.form)
    try:
        pdf_path, download_name = gerar_pdf_relatorio(
            codigo_usina=codigo_usina,
            ano=filtros["ano"],
        )
    except Exception as exc:
        return (
            render_template(
                "componentes/reports.html",
                codigo_usina=codigo_usina,
                username=session.get("username", ""),
                active_page="reports",
                anos_relatorio=listar_anos_relatorio(),
                ano_selecionado=filtros["ano"],
                erro=f"Falha ao gerar relatorio: {exc}",
            ),
            500,
        )

    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=download_name,
        mimetype="application/pdf",
        max_age=0,
    )


@dashboard_bp.route("/health")
@desempenho
def health():
    return jsonify({"status": "ok"}), 200
