# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. create_app             -> Inicializa a aplicação Flask
# 2. internal_server_error  -> Trata erros HTTP 500
# 3. handle_exception       -> Trata exceções não mapeadas
# 4. bootstrap principal    -> Sobe o servidor local
# -------------------------------------------------------------------

import os
import traceback

from flask import Flask, render_template
from werkzeug.exceptions import HTTPException

from libs.models.utils import register_template_filters
from libs.views.servicos.connect import socketio, registrar_eventos, iniciar_emissao_periodica

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "libs", "views")
STATIC_DIR = os.path.join(BASE_DIR, "assets")
DEV_RELOAD = os.getenv("DEV_RELOAD", "0") == "1"


def create_app():
    app = Flask(
        __name__,
        template_folder=TEMPLATE_DIR,
        static_folder=STATIC_DIR,
        static_url_path="/assets",
    )

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me")

    @app.errorhandler(500)
    def internal_server_error(erro):
        return render_template("error.html", error_code=500, error_msg=str(erro)), 500

    @app.errorhandler(Exception)
    def handle_exception(erro):
        if isinstance(erro, HTTPException):
            return erro

        trace = traceback.format_exc()
        print(f"[ERROR] Excecao nao tratada: {erro}\n{trace}", flush=True)
        return (
            render_template(
                "error.html",
                error_code=500,
                error_msg="Erro interno inesperado",
                debug_trace=trace if DEV_RELOAD else None,
            ),
            500,
        )

    register_template_filters(app)

    from libs.routes.routes import dashboard_bp

    app.register_blueprint(dashboard_bp)

    socketio.init_app(app, cors_allowed_origins="*")
    registrar_eventos()

    return app


app = create_app()
iniciar_emissao_periodica(app)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = DEV_RELOAD or os.getenv("FLASK_DEBUG", "0") == "1"
    host = "0.0.0.0"

    print(f"[MAIN] Iniciando servidor em {host}:{port} (DEV_RELOAD={debug})", flush=True)
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)
