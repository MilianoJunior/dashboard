# -------------------------------------------------------------------
# FLUXO DO MODULO
# 1. test_login_correto          -> Senha correta retorna (True, usina_obj)
# 2. test_login_senha_errada     -> Senha errada retorna (False, None)
# 3. test_login_usina_inexistente -> Usina fora do config retorna (False, None)
# 4. test_login_espacos          -> Espacos em branco sao tratados
# 5. test_todas_usinas           -> Cada usina aceita sua senha correta
# -------------------------------------------------------------------

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import patch, MagicMock

# Mock streamlit e yaml write
sys.modules['streamlit'] = MagicMock()

from libs.controllers.auth import authenticate_user


USINAS_CONFIG = {
    "CGH-FAE": {"users": "cgh-fae", "tabela": "cgh_fae"},
    "CGH-APARECIDA": {"users": "cgh-aparecida", "tabela": "cgh_aparecida"},
    "PCH-PEDRAS": {"users": "pch-pedras", "tabela": "pch_pedras"},
    "CGH-PICADAS-ALTAS": {"users": "cgh-picadas-altas", "tabela": "cgh_picadas_altas"},
    "CGH-HOPPEN": {"users": "cgh-hoppen", "tabela": "cgh_hoppen"},
    "PCH-PIRA": {"users": "pch-pira"},
}

SENHAS_CORRETAS = {
    "CGH-FAE": "fae102",
    "CGH-PICADAS-ALTAS": "picadas104",
    "PCH-PEDRAS": "pedras25",
    "CGH-APARECIDA": "aparecida103",
    "CGH-HOPPEN": "hoppen80",
    "PCH-PIRA": "pira123",
}

ESPERADO = {
    "test_login_correto": {"autenticado": True, "usina_nome": "CGH-FAE"},
    "test_login_senha_errada": {"autenticado": False},
    "test_login_usina_inexistente": {"autenticado": False},
    "test_login_espacos": {"autenticado": True},
    "test_todas_usinas": {"todas_autenticam": True},
}


@patch("libs.controllers.auth.register_user")
def test_login_correto(mock_register):
    nome = "test_login_correto"
    esp = ESPERADO[nome]
    try:
        usina = esp["usina_nome"]
        autenticado, obj = authenticate_user("admin", SENHAS_CORRETAS[usina], usina, USINAS_CONFIG)
        erros = []

        if autenticado != esp["autenticado"]:
            erros.append(f"Esperava autenticado={esp['autenticado']}, obteve {autenticado}")
        if obj is None:
            erros.append("Objeto usina retornou None")
        elif obj.get("users") != USINAS_CONFIG[usina]["users"]:
            erros.append(f"Objeto usina incorreto: {obj}")

        if erros:
            return nome, False, erros
        return nome, True, f"Login {usina} OK"
    except Exception as e:
        return nome, False, [str(e)]


@patch("libs.controllers.auth.register_user")
def test_login_senha_errada(mock_register):
    nome = "test_login_senha_errada"
    try:
        autenticado, obj = authenticate_user("admin", "senha_errada", "CGH-FAE", USINAS_CONFIG)
        erros = []

        if autenticado != False:
            erros.append(f"Deveria falhar, mas autenticou: {autenticado}")
        if obj is not None:
            erros.append(f"Objeto deveria ser None, obteve: {obj}")

        if erros:
            return nome, False, erros
        return nome, True, "Senha errada rejeitada"
    except Exception as e:
        return nome, False, [str(e)]


@patch("libs.controllers.auth.register_user")
def test_login_usina_inexistente(mock_register):
    nome = "test_login_usina_inexistente"
    try:
        autenticado, obj = authenticate_user("admin", "qualquer", "USINA-FANTASMA", USINAS_CONFIG)
        erros = []

        if autenticado != False:
            erros.append(f"Deveria falhar, mas autenticou")
        if obj is not None:
            erros.append(f"Objeto deveria ser None")

        if erros:
            return nome, False, erros
        return nome, True, "Usina inexistente rejeitada"
    except Exception as e:
        return nome, False, [str(e)]


@patch("libs.controllers.auth.register_user")
def test_login_espacos(mock_register):
    nome = "test_login_espacos"
    try:
        autenticado, obj = authenticate_user("  admin  ", "  fae102  ", "CGH-FAE", USINAS_CONFIG)
        erros = []

        if autenticado != True:
            erros.append("Login com espacos deveria funcionar apos strip")

        if erros:
            return nome, False, erros
        return nome, True, "Espacos tratados corretamente"
    except Exception as e:
        return nome, False, [str(e)]


@patch("libs.controllers.auth.register_user")
def test_todas_usinas(mock_register):
    nome = "test_todas_usinas"
    try:
        erros = []
        for usina, senha in SENHAS_CORRETAS.items():
            autenticado, obj = authenticate_user("admin", senha, usina, USINAS_CONFIG)
            if not autenticado:
                erros.append(f"{usina}: nao autenticou com senha correta")

        if erros:
            return nome, False, erros
        return nome, True, f"Todas as {len(SENHAS_CORRETAS)} usinas autenticaram"
    except Exception as e:
        return nome, False, [str(e)]


TODOS = [
    test_login_correto,
    test_login_senha_errada,
    test_login_usina_inexistente,
    test_login_espacos,
    test_todas_usinas,
]
