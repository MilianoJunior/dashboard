# -------------------------------------------------------------------
# FLUXO DO MODULO
# 1. test_rename_colunas_ug       -> Renomeia colunas UG corretamente
# 2. test_rename_colunas_sem_ug   -> Colunas sem UG ficam inalteradas
# 3. test_percentual_positivo     -> Icone azul para percentual > 0
# 4. test_percentual_negativo     -> Icone vermelho para percentual < 0
# 5. test_percentual_none         -> Retorna string vazia para None
# -------------------------------------------------------------------

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd

# Mock do streamlit antes de importar
from unittest.mock import MagicMock
sys.modules['streamlit'] = MagicMock()
sys.modules['extra_streamlit_components'] = MagicMock()
sys.modules['plotly'] = MagicMock()
sys.modules['plotly.graph_objects'] = MagicMock()
sys.modules['plotly.express'] = MagicMock()

from libs.views.componentes import rename_colunas, render_percentual_icon


ESPERADO = {
    "test_rename_colunas_ug": {
        "entrada": ["ug_01_energia", "ug_02_energia", "data_hora"],
        "saida_contem": ["UG-01 (MWh)", "UG-02 (MWh)"],
        "saida_nao_renomeia": ["data_hora"],
    },
    "test_rename_colunas_sem_ug": {
        "entrada": ["temperatura", "pressao", "nivel"],
        "saida_igual_entrada": True,
    },
    "test_percentual_positivo": {
        "valor": 15.5,
        "cor": "#3A80EF",
        "contem_svg": True,
    },
    "test_percentual_negativo": {
        "valor": -8.3,
        "cor": "#EF6A6A",
        "contem_svg": True,
    },
    "test_percentual_none": {
        "valor": None,
        "retorno": "",
    },
}


def test_rename_colunas_ug():
    nome = "test_rename_colunas_ug"
    esp = ESPERADO[nome]
    try:
        df = pd.DataFrame({col: [1.0] for col in esp["entrada"]})
        resultado = rename_colunas(df)
        erros = []

        for col_esperada in esp["saida_contem"]:
            if col_esperada not in resultado.columns:
                erros.append(f"Coluna '{col_esperada}' nao encontrada em {list(resultado.columns)}")

        for col_fixa in esp["saida_nao_renomeia"]:
            if col_fixa not in resultado.columns:
                erros.append(f"Coluna '{col_fixa}' deveria permanecer mas sumiu")

        if erros:
            return nome, False, erros
        return nome, True, f"Colunas renomeadas: {list(resultado.columns)}"
    except Exception as e:
        return nome, False, [str(e)]


def test_rename_colunas_sem_ug():
    nome = "test_rename_colunas_sem_ug"
    esp = ESPERADO[nome]
    try:
        df = pd.DataFrame({col: [1.0] for col in esp["entrada"]})
        resultado = rename_colunas(df)
        erros = []

        if list(resultado.columns) != esp["entrada"]:
            erros.append(f"Colunas mudaram: {list(resultado.columns)} != {esp['entrada']}")

        if erros:
            return nome, False, erros
        return nome, True, f"Colunas inalteradas: {list(resultado.columns)}"
    except Exception as e:
        return nome, False, [str(e)]


def test_percentual_positivo():
    nome = "test_percentual_positivo"
    esp = ESPERADO[nome]
    try:
        html = render_percentual_icon(esp["valor"])
        erros = []

        if not isinstance(html, str):
            erros.append(f"Retorno nao e string: {type(html)}")
        elif esp["cor"] not in html:
            erros.append(f"Cor '{esp['cor']}' nao encontrada no HTML")
        elif "<svg" not in html:
            erros.append("SVG nao encontrado no HTML")

        if erros:
            return nome, False, erros
        return nome, True, f"Icone azul com {esp['valor']}%"
    except Exception as e:
        return nome, False, [str(e)]


def test_percentual_negativo():
    nome = "test_percentual_negativo"
    esp = ESPERADO[nome]
    try:
        html = render_percentual_icon(esp["valor"])
        erros = []

        if not isinstance(html, str):
            erros.append(f"Retorno nao e string: {type(html)}")
        elif esp["cor"] not in html:
            erros.append(f"Cor '{esp['cor']}' nao encontrada no HTML")
        elif "<svg" not in html:
            erros.append("SVG nao encontrado no HTML")

        if erros:
            return nome, False, erros
        return nome, True, f"Icone vermelho com {esp['valor']}%"
    except Exception as e:
        return nome, False, [str(e)]


def test_percentual_none():
    nome = "test_percentual_none"
    esp = ESPERADO[nome]
    try:
        html = render_percentual_icon(esp["valor"])
        if html != esp["retorno"]:
            return nome, False, [f"Esperava '{esp['retorno']}', obteve '{html}'"]
        return nome, True, "None -> string vazia"
    except Exception as e:
        return nome, False, [str(e)]


TODOS = [
    test_rename_colunas_ug,
    test_rename_colunas_sem_ug,
    test_percentual_positivo,
    test_percentual_negativo,
    test_percentual_none,
]
