# -------------------------------------------------------------------
# FLUXO DO MODULO
# 1. test_carrega_yaml_valido        -> YAML carrega e retorna dict com "usinas"
# 2. test_campos_obrigatorios        -> Cada usina tem users, tabela, energia, nivel
# 3. test_usinas_esperadas           -> Lista de usinas bate com o esperado
# 4. test_nivel_vertimento_numerico  -> nivel_vertimento converte para float
# -------------------------------------------------------------------

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from libs.controllers.config_controller import load_app_config


ESPERADO = {
    "test_carrega_yaml_valido": {
        "tipo_retorno": dict,
        "tem_chave_usinas": True,
    },
    "test_campos_obrigatorios": {
        "campos": ["users", "tabela", "energia", "nivel"],
        "todas_possuem": True,
        "excecoes": ["PCH-PIRA"],  # configuracao parcial (sem tabela/energia/nivel)
    },
    "test_usinas_esperadas": {
        "usinas": ["CGH-APARECIDA", "CGH-FAE", "PCH-PEDRAS", "CGH-PICADAS-ALTAS", "CGH-HOPPEN", "PCH-PIRA"],
    },
    "test_nivel_vertimento_numerico": {
        "todos_convertem": True,
    },
}


def test_carrega_yaml_valido():
    nome = "test_carrega_yaml_valido"
    try:
        config = load_app_config(deploy_mode=True)
        erros = []

        if not isinstance(config, ESPERADO[nome]["tipo_retorno"]):
            erros.append(f"Tipo esperado {ESPERADO[nome]['tipo_retorno']}, obteve {type(config)}")

        if ("usinas" in config) != ESPERADO[nome]["tem_chave_usinas"]:
            erros.append("Chave 'usinas' nao encontrada no config")

        if erros:
            return nome, False, erros
        return nome, True, "Config carregado com chave 'usinas'"
    except Exception as e:
        return nome, False, [str(e)]


def test_campos_obrigatorios():
    nome = "test_campos_obrigatorios"
    try:
        config = load_app_config(deploy_mode=True)
        campos = ESPERADO[nome]["campos"]
        erros = []

        excecoes = ESPERADO[nome].get("excecoes", [])
        for usina_nome, usina_cfg in config["usinas"].items():
            if usina_nome in excecoes:
                continue
            for campo in campos:
                if campo not in usina_cfg:
                    erros.append(f"{usina_nome}: campo '{campo}' ausente")

        if erros:
            return nome, False, erros
        return nome, True, f"Todas as usinas possuem {campos}"
    except Exception as e:
        return nome, False, [str(e)]


def test_usinas_esperadas():
    nome = "test_usinas_esperadas"
    try:
        config = load_app_config(deploy_mode=True)
        usinas_encontradas = list(config["usinas"].keys())
        usinas_esperadas = ESPERADO[nome]["usinas"]
        erros = []

        for u in usinas_esperadas:
            if u not in usinas_encontradas:
                erros.append(f"Usina '{u}' esperada mas nao encontrada")

        for u in usinas_encontradas:
            if u not in usinas_esperadas:
                erros.append(f"Usina '{u}' encontrada mas nao esperada")

        if erros:
            return nome, False, erros
        return nome, True, f"{len(usinas_encontradas)} usinas encontradas"
    except Exception as e:
        return nome, False, [str(e)]


def test_nivel_vertimento_numerico():
    nome = "test_nivel_vertimento_numerico"
    try:
        config = load_app_config(deploy_mode=True)
        erros = []

        for usina_nome, usina_cfg in config["usinas"].items():
            nv = usina_cfg.get("nivel_vertimento")
            if nv is None:
                continue
            try:
                float(nv)
            except (ValueError, TypeError):
                erros.append(f"{usina_nome}: nivel_vertimento '{nv}' nao e numerico")

        if erros:
            return nome, False, erros
        return nome, True, "Todos os nivel_vertimento convertem para float"
    except Exception as e:
        return nome, False, [str(e)]


TODOS = [
    test_carrega_yaml_valido,
    test_campos_obrigatorios,
    test_usinas_esperadas,
    test_nivel_vertimento_numerico,
]
