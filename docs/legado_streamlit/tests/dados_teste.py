# -------------------------------------------------------------------
# FLUXO DO MODULO
# 1. CONFIG_USINAS        -> Config YAML simulada (2 usinas)
# 2. RESPOSTA_PRODUCAO    -> Resposta simulada de /producao-acumulada
# 3. RESPOSTA_NIVEL       -> Resposta simulada de /grupo-usina (hidraulica)
# 4. RESPOSTA_GRUPOS      -> Resposta simulada de /grupos/{usina}
# 5. df_energia_diario    -> DataFrame com energia de 5 dias
# 6. df_energia_mensal    -> DataFrame com energia de 4 meses
# 7. df_energia_horario   -> DataFrame com energia de 24 horas
# -------------------------------------------------------------------

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


# -------------------------------------------------------------------
# CONFIG SIMULADA
# -------------------------------------------------------------------
CONFIG_USINAS = {
    "usinas": {
        "CGH-TESTE-1UG": {
            "users": "cgh-teste",
            "tabela": "cgh_teste",
            "nivel_vertimento": "405.28",
            "energia": {
                "data_hora": "data_hora",
                "energia_ug01": "acumulador_energia",
            },
            "nivel": {
                "nivel_montante": "nivel_montante",
                "nivel_jusante": "nivel_jusante",
            },
            "cols_energia": "data_hora,energia_ug01",
            "cols_nivel": "data_hora,nivel_montante,nivel_jusante",
        },
        "PCH-TESTE-2UG": {
            "users": "pch-teste",
            "tabela": {"ug01": "pch_teste_ug01", "ug02": "pch_teste_ug02"},
            "nivel_vertimento": "1097.5",
            "energia": {
                "ug01": {"data_hora": "data_hora", "energia_ug01": "acum_energia"},
                "ug02": {"data_hora": "data_hora", "energia_ug02": "acum_energia"},
            },
            "nivel": {
                "ug01": {"nivel_montante": "niv_mont_grade"},
                "ug02": {"nivel_jusante_ug02": "niv_jus_grade"},
            },
            "cols_energia": "data_hora,energia_ug01,energia_ug02",
            "cols_nivel": "data_hora,nivel_montante,nivel_jusante_ug02",
        },
    }
}


# -------------------------------------------------------------------
# RESPOSTAS SIMULADAS DA API
# -------------------------------------------------------------------
RESPOSTA_PRODUCAO_DIARIA = {
    "resultado": [
        {"data": "2026-03-01", "UG-01 Energia Acumulada": 100.5},
        {"data": "2026-03-02", "UG-01 Energia Acumulada": 85.3},
        {"data": "2026-03-03", "UG-01 Energia Acumulada": 92.1},
    ]
}

RESPOSTA_PRODUCAO_MENSAL = {
    "resultado": [
        {"periodo": "2026-01", "total": 6157.27},
        {"periodo": "2026-02", "total": 4334.64},
        {"periodo": "2026-03", "total": 3213.36},
    ]
}

RESPOSTA_NIVEL = {
    "dados": [
        {"data_hora": "2026-03-01T08:00:00", "Nivel Montante": 390.5, "Nivel Jusante": 385.2},
        {"data_hora": "2026-03-01T09:00:00", "Nivel Montante": 390.6, "Nivel Jusante": 385.3},
        {"data_hora": "2026-03-01T10:00:00", "Nivel Montante": 390.4, "Nivel Jusante": 385.1},
    ]
}

RESPOSTA_GRUPOS = {
    "energia": ["UG-01 Energia Acumulada"],
    "potencia": ["UG-01 Potencia Ativa", "UG-01 Potencia Reativa"],
    "hidraulica": ["Nivel Montante", "Nivel Jusante"],
}

RESPOSTA_SENSOR = {
    "usina": "CGH-TESTE",
    "variavel": "UG-01 Potencia Ativa",
    "registros": 3,
    "dados": [
        {"data_hora": "2026-03-01T08:00:00", "UG-01 Potencia Ativa": 125.4},
        {"data_hora": "2026-03-01T08:01:00", "UG-01 Potencia Ativa": 124.8},
        {"data_hora": "2026-03-01T08:02:00", "UG-01 Potencia Ativa": 126.1},
    ],
}


# -------------------------------------------------------------------
# DATAFRAMES SINTETICOS
# -------------------------------------------------------------------
def df_energia_diario():
    """5 dias de dados com energia acumulada crescente."""
    base = datetime(2026, 3, 1)
    registros = []
    energia_acum = 1000.0
    for dia in range(5):
        for hora in range(0, 24):
            energia_acum += round(np.random.uniform(0.1, 0.5), 2)
            registros.append({
                "data_hora": base + timedelta(days=dia, hours=hora),
                "energia_ug01": round(energia_acum, 2),
            })
    return pd.DataFrame(registros)


def df_energia_mensal():
    """4 meses de dados com energia acumulada crescente."""
    base = datetime(2026, 1, 1)
    registros = []
    energia_acum = 5000.0
    for mes in range(4):
        dias_no_mes = [31, 28, 31, 30][mes]
        for dia in range(dias_no_mes):
            energia_acum += round(np.random.uniform(5.0, 15.0), 2)
            registros.append({
                "data_hora": base + timedelta(days=sum([31, 28, 31, 30][:mes]) + dia),
                "energia_ug01": round(energia_acum, 2),
            })
    return pd.DataFrame(registros)


def df_energia_horario():
    """24 horas de dados (1 registro por minuto)."""
    base = datetime(2026, 3, 1)
    registros = []
    energia_acum = 2000.0
    for minuto in range(24 * 60):
        energia_acum += round(np.random.uniform(0.005, 0.02), 4)
        registros.append({
            "data_hora": base + timedelta(minutes=minuto),
            "energia_ug01": round(energia_acum, 2),
        })
    return pd.DataFrame(registros)


def df_energia_com_outlier():
    """DataFrame com valor 103.00 (outlier conhecido)."""
    base = datetime(2026, 3, 1)
    registros = [
        {"data_hora": base, "energia_ug01": 1000.0},
        {"data_hora": base + timedelta(hours=1), "energia_ug01": 1005.0},
        {"data_hora": base + timedelta(hours=2), "energia_ug01": 103.00},  # outlier
        {"data_hora": base + timedelta(hours=3), "energia_ug01": 1015.0},
    ]
    return pd.DataFrame(registros)
