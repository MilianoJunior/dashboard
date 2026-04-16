# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. create_app             -> Inicializa a aplicação Flask
# 2. internal_server_error  -> Trata erros HTTP 500
# 3. handle_exception       -> Trata exceções não mapeadas
# 4. abrir_navegador        -> Abre Chrome em janela dedicada ao iniciar
# 5. fechar_navegador       -> Fecha janela e limpa profile temporário
# 6. bootstrap principal    -> Sobe o servidor local
# -------------------------------------------------------------------

import atexit
import os
import shutil
import subprocess
import tempfile
import threading
import time
import traceback
import webbrowser

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

# --------------- Gerenciamento do navegador ---------------
_CHROME_BINS = ['google-chrome', 'google-chrome-stable', 'chromium-browser', 'chromium']
_browser_proc = None
_browser_profile = None


def abrir_navegador(url, delay=1.5):
    """Abre Chrome em janela dedicada (instância separada) após delay."""
    def _abrir():
        global _browser_proc, _browser_profile
        time.sleep(delay)

        chrome = next((c for c in _CHROME_BINS if shutil.which(c)), None)
        if chrome:
            _browser_profile = tempfile.mkdtemp(prefix="dashboard_")
            args = [
                chrome, f'--app={url}', f'--user-data-dir={_browser_profile}',
                '--no-first-run', '--no-default-browser-check'
            ]
            
            width = 1900
            height = 1000
            if width and height:
                args.append(f'--window-size={width},{height}')
            else:
                args.append('--start-maximized')

            pos_x = os.getenv("CHROME_POS_X", "5400")
            pos_y = os.getenv("CHROME_POS_Y", "400")
            print(f'pos_x: {pos_x}, pos_y: {pos_y}, width: {width}, height: {height}')
            if pos_x is not None:
                args.append(f'--window-position={pos_x},{pos_y}')

            _browser_proc = subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        else:
            webbrowser.open(url)

    threading.Thread(target=_abrir, daemon=True).start()


def fechar_navegador():
    """Fecha a janela dedicada e remove profile temporário."""
    global _browser_proc, _browser_profile
    if _browser_proc:
        try:
            _browser_proc.terminate()
            _browser_proc.wait(timeout=3)
        except Exception:
            pass
        _browser_proc = None
    if _browser_profile and os.path.exists(_browser_profile):
        shutil.rmtree(_browser_profile, ignore_errors=True)
        _browser_profile = None


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = DEV_RELOAD or os.getenv("FLASK_DEBUG", "0") == "1"
    host = "0.0.0.0"
    print(os.environ.get("WERKZEUG_RUN_MAIN"))

    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        print("entrou")
        abrir_navegador(f"http://localhost:{port}")
        atexit.register(fechar_navegador)

    print(f"[MAIN] Iniciando servidor em {host}:{port} (DEV_RELOAD={debug})", flush=True)
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True, use_reloader=False)