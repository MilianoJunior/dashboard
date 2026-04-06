# -------------------------------------------------------------------
# FLUXO DO MODULO
# 1. test_energia_diario     -> Calculo diario produz diff correto
# 2. test_energia_mensal     -> Calculo mensal produz diff correto
# 3. test_energia_horario    -> Calculo horario produz diff correto
# 4. test_outlier_103        -> Linhas com 103.00 sao removidas
# 5. test_retira_outliers    -> Clip de valores extremos
# -------------------------------------------------------------------

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np

# Mock do streamlit antes de importar calculos
from unittest.mock import MagicMock
sys.modules['streamlit'] = MagicMock()

from libs.models.calculos import calcular_energia_acumulada, retira_outliers
from tests.dados_teste import (
    df_energia_diario,
    df_energia_mensal,
    df_energia_horario,
    df_energia_com_outlier,
)


ESPERADO = {
    "test_energia_diario": {
        "periodo": "D",
        "colunas_resultado_contem": "prod_",
        "valores_positivos": True,
        "min_linhas": 4,  # 5 dias - 1 (diff perde o primeiro)
    },
    "test_energia_mensal": {
        "periodo": "M",
        "colunas_resultado_contem": "prod_",
        "valores_positivos": True,
        "min_linhas": 2,
    },
    "test_energia_horario": {
        "periodo": "H",
        "colunas_resultado_contem": "prod_",
        "valores_positivos": True,
        "min_linhas": 20,
    },
    "test_outlier_103": {
        "valor_103_presente": False,
    },
    "test_retira_outliers": {
        "dentro_do_range": True,
    },
}


def test_energia_diario():
    nome = "test_energia_diario"
    esp = ESPERADO[nome]
    try:
        df = df_energia_diario()
        colunas = list(df.columns)
        resultado = calcular_energia_acumulada(df, colunas, esp["periodo"])
        erros = []

        # Tem colunas com prefixo prod_
        cols_prod = [c for c in resultado.columns if esp["colunas_resultado_contem"] in c]
        if not cols_prod:
            erros.append(f"Nenhuma coluna com '{esp['colunas_resultado_contem']}' encontrada: {list(resultado.columns)}")

        # Valores sao positivos (energia acumulada so cresce)
        if cols_prod:
            negativos = (resultado[cols_prod] < 0).any().any()
            if negativos and esp["valores_positivos"]:
                erros.append("Encontrados valores negativos na producao diaria")

        # Minimo de linhas
        if len(resultado) < esp["min_linhas"]:
            erros.append(f"Esperava >= {esp['min_linhas']} linhas, obteve {len(resultado)}")

        if erros:
            return nome, False, erros
        return nome, True, f"{len(resultado)} dias, colunas: {cols_prod}"
    except Exception as e:
        return nome, False, [str(e)]


def test_energia_mensal():
    nome = "test_energia_mensal"
    esp = ESPERADO[nome]
    try:
        df = df_energia_mensal()
        colunas = list(df.columns)
        resultado = calcular_energia_acumulada(df, colunas, esp["periodo"])
        erros = []

        cols_prod = [c for c in resultado.columns if esp["colunas_resultado_contem"] in c]
        if not cols_prod:
            erros.append(f"Nenhuma coluna com '{esp['colunas_resultado_contem']}' encontrada")

        if len(resultado) < esp["min_linhas"]:
            erros.append(f"Esperava >= {esp['min_linhas']} linhas, obteve {len(resultado)}")

        if erros:
            return nome, False, erros
        return nome, True, f"{len(resultado)} meses, colunas: {cols_prod}"
    except Exception as e:
        return nome, False, [str(e)]


def test_energia_horario():
    nome = "test_energia_horario"
    esp = ESPERADO[nome]
    try:
        df = df_energia_horario()
        colunas = list(df.columns)
        resultado = calcular_energia_acumulada(df, colunas, esp["periodo"])
        erros = []

        cols_prod = [c for c in resultado.columns if esp["colunas_resultado_contem"] in c]
        if not cols_prod:
            erros.append(f"Nenhuma coluna com '{esp['colunas_resultado_contem']}' encontrada")

        if len(resultado) < esp["min_linhas"]:
            erros.append(f"Esperava >= {esp['min_linhas']} linhas, obteve {len(resultado)}")

        if erros:
            return nome, False, erros
        return nome, True, f"{len(resultado)} horas, colunas: {cols_prod}"
    except Exception as e:
        return nome, False, [str(e)]


def test_outlier_103():
    nome = "test_outlier_103"
    esp = ESPERADO[nome]
    try:
        df = df_energia_com_outlier()
        colunas = list(df.columns)
        resultado = calcular_energia_acumulada(df, colunas, "H")
        erros = []

        # Verifica que o valor 103.00 foi removido antes do calculo
        # O resultado nao deve conter linhas derivadas do 103
        cols_prod = [c for c in resultado.columns if "prod_" in c]
        if cols_prod:
            # Se 103 foi filtrado, nao deve haver saltos gigantes negativos
            for c in cols_prod:
                vals = resultado[c].values
                grandes_negativos = [v for v in vals if v < -100]
                if grandes_negativos:
                    erros.append(f"Coluna {c} tem salto negativo grande: {grandes_negativos} (103 nao foi filtrado?)")

        if erros:
            return nome, False, erros
        return nome, True, "Outlier 103.00 tratado corretamente"
    except Exception as e:
        return nome, False, [str(e)]


def test_retira_outliers():
    nome = "test_retira_outliers"
    esp = ESPERADO[nome]
    try:
        # DataFrame com outliers extremos
        df = pd.DataFrame({
            "data_hora": pd.date_range("2026-01-01", periods=100, freq="h"),
            "valor": list(range(100)),
        })
        # Injeta outliers
        df.loc[0, "valor"] = -9999
        df.loc[99, "valor"] = 9999

        resultado = retira_outliers(df, ["valor"])
        erros = []

        val_min = resultado["valor"].min()
        val_max = resultado["valor"].max()

        if val_min <= -9999:
            erros.append(f"Outlier inferior nao removido: {val_min}")
        if val_max >= 9999:
            erros.append(f"Outlier superior nao removido: {val_max}")

        if erros:
            return nome, False, erros
        return nome, True, f"Valores clippados entre {val_min} e {val_max}"
    except Exception as e:
        return nome, False, [str(e)]


TODOS = [
    test_energia_diario,
    test_energia_mensal,
    test_energia_horario,
    test_outlier_103,
    test_retira_outliers,
]
