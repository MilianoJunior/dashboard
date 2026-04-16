import json
import os
from functools import wraps

from flask import redirect, session, url_for

_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_USUARIOS_PATH = os.path.join(_BASE_DIR, "config", "usuarios.json")


def _carregar_usuarios():
    with open(_USUARIOS_PATH, "r", encoding="utf-8") as f:
        return json.load(f).get("usuarios", [])


def autenticar(username, password):
    username = (username or "").strip()
    password = password or ""
    for u in _carregar_usuarios():
        if u.get("username") == username: # and u.get("password") == password:
            return u.get("usina")
    return None


def login_required(view):
    @wraps(view)
    def _wrapped(*args, **kwargs):
        if not session.get("codigo_usina"):
            return redirect(url_for("dashboard.login"))
        return view(*args, **kwargs)

    return _wrapped
