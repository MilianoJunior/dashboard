# -------------------------------------------------------------------
# FLUXO DO MODULO
# 1. test_parse_data_periodo_dia     -> Parse de data trunca para dia
# 2. test_parse_data_periodo_hora    -> Parse de data preserva hora
# 3. test_parse_data_periodo_mes     -> Parse de data trunca para mes
# 4. test_parse_data_formatos        -> Parse aceita multiplos formatos
# 5. test_parse_data_none            -> Parse de None retorna None
# 6. test_obter_valor_total_mwh      -> Extrai total de diferentes registros
# 7. test_normalizar_energia         -> Converte resposta API em DataFrame
# 8. test_normalizar_nivel           -> Converte resposta nivel em DataFrame
# 9. test_normalizar_cards           -> Converte resposta mensal em dict cards
# -------------------------------------------------------------------

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime

# Mock do streamlit antes de importar
from unittest.mock import MagicMock
sys.modules['streamlit'] = MagicMock()

from libs.controllers.data_controller import (
    _parse_data_periodo,
    _obter_valor_total_mwh,
    _normalizar_grafico_energia_api,
    _normalizar_grafico_nivel_api,
    _normalizar_cards_calculadora,
)
from tests.dados_teste import (
    RESPOSTA_PRODUCAO_DIARIA,
    RESPOSTA_PRODUCAO_MENSAL,
    RESPOSTA_NIVEL,
)


ESPERADO = {
    "test_parse_data_periodo_dia": {
        "entrada": "2026-03-15 14:30:00",
        "periodo": "D",
        "hora_esperada": 0,
        "minuto_esperado": 0,
        "dia_esperado": 15,
    },
    "test_parse_data_periodo_hora": {
        "entrada": "2026-03-15 14:30:00",
        "periodo": "H",
        "hora_esperada": 14,
        "minuto_esperado": 30,
    },
    "test_parse_data_periodo_mes": {
        "entrada": "2026-03-15 14:30:00",
        "periodo": "M",
        "dia_esperado": 1,
        "hora_esperada": 0,
    },
    "test_parse_data_formatos": {
        "entradas": [
            ("2026-03-15T14:30:00", "D"),
            ("2026-03-15 14:30:00", "D"),
            ("2026-03-15 14:30", "D"),
            ("15/03/2026 14:30", "D"),
            ("2026-03-15", "D"),
            ("2026-03", "M"),
        ],
        "todas_retornam_datetime": True,
    },
    "test_parse_data_none": {"retorno": None},
    "test_obter_valor_total_mwh": {
        "registro_com_total": {"total": 150.5, "data": "2026-03"},
        "valor_esperado_total": 150.5,
        "registro_com_soma": {"prod_ug01": 80.0, "prod_ug02": 70.5, "data": "2026-03"},
        "valor_esperado_soma": 150.5,
        "registro_vazio": {"data": "2026-03", "nome": "teste"},
        "valor_esperado_vazio": None,
    },
    "test_normalizar_energia": {
        "min_linhas": 3,
        "index_tipo": "datetime",
        "valores_numericos": True,
    },
    "test_normalizar_nivel": {
        "min_linhas": 3,
        "index_tipo": "datetime",
        "valores_numericos": True,
    },
    "test_normalizar_cards": {
        "min_cards": 3,
        "card_tem_chaves": ["value", "medida", "percentual"],
    },
}


def test_parse_data_periodo_dia():
    nome = "test_parse_data_periodo_dia"
    esp = ESPERADO[nome]
    try:
        resultado = _parse_data_periodo(esp["entrada"], esp["periodo"])
        erros = []

        if resultado is None:
            erros.append("Retornou None")
        elif resultado.hour != esp["hora_esperada"]:
            erros.append(f"Hora esperada {esp['hora_esperada']}, obteve {resultado.hour}")
        elif resultado.minute != esp["minuto_esperado"]:
            erros.append(f"Minuto esperado {esp['minuto_esperado']}, obteve {resultado.minute}")
        elif resultado.day != esp["dia_esperado"]:
            erros.append(f"Dia esperado {esp['dia_esperado']}, obteve {resultado.day}")

        if erros:
            return nome, False, erros
        return nome, True, f"Parse D: {esp['entrada']} -> {resultado}"
    except Exception as e:
        return nome, False, [str(e)]


def test_parse_data_periodo_hora():
    nome = "test_parse_data_periodo_hora"
    esp = ESPERADO[nome]
    try:
        resultado = _parse_data_periodo(esp["entrada"], esp["periodo"])
        erros = []

        if resultado is None:
            erros.append("Retornou None")
        elif resultado.hour != esp["hora_esperada"]:
            erros.append(f"Hora esperada {esp['hora_esperada']}, obteve {resultado.hour}")
        elif resultado.minute != esp["minuto_esperado"]:
            erros.append(f"Minuto esperado {esp['minuto_esperado']}, obteve {resultado.minute}")

        if erros:
            return nome, False, erros
        return nome, True, f"Parse H: {esp['entrada']} -> {resultado}"
    except Exception as e:
        return nome, False, [str(e)]


def test_parse_data_periodo_mes():
    nome = "test_parse_data_periodo_mes"
    esp = ESPERADO[nome]
    try:
        resultado = _parse_data_periodo(esp["entrada"], esp["periodo"])
        erros = []

        if resultado is None:
            erros.append("Retornou None")
        elif resultado.day != esp["dia_esperado"]:
            erros.append(f"Dia esperado {esp['dia_esperado']}, obteve {resultado.day}")
        elif resultado.hour != esp["hora_esperada"]:
            erros.append(f"Hora esperada {esp['hora_esperada']}, obteve {resultado.hour}")

        if erros:
            return nome, False, erros
        return nome, True, f"Parse M: {esp['entrada']} -> {resultado}"
    except Exception as e:
        return nome, False, [str(e)]


def test_parse_data_formatos():
    nome = "test_parse_data_formatos"
    esp = ESPERADO[nome]
    try:
        erros = []
        for entrada, periodo in esp["entradas"]:
            resultado = _parse_data_periodo(entrada, periodo)
            if not isinstance(resultado, datetime):
                erros.append(f"'{entrada}' ({periodo}) -> {resultado} (nao e datetime)")

        if erros:
            return nome, False, erros
        return nome, True, f"Todos os {len(esp['entradas'])} formatos parseados"
    except Exception as e:
        return nome, False, [str(e)]


def test_parse_data_none():
    nome = "test_parse_data_none"
    try:
        resultado = _parse_data_periodo(None, "D")
        if resultado is not ESPERADO[nome]["retorno"]:
            return nome, False, [f"Esperava None, obteve {resultado}"]
        return nome, True, "None -> None"
    except Exception as e:
        return nome, False, [str(e)]


def test_obter_valor_total_mwh():
    nome = "test_obter_valor_total_mwh"
    esp = ESPERADO[nome]
    try:
        erros = []

        # Registro com chave "total"
        val = _obter_valor_total_mwh(esp["registro_com_total"])
        if val != esp["valor_esperado_total"]:
            erros.append(f"Registro com total: esperado {esp['valor_esperado_total']}, obteve {val}")

        # Registro com soma de producoes
        val = _obter_valor_total_mwh(esp["registro_com_soma"])
        if val != esp["valor_esperado_soma"]:
            erros.append(f"Registro com soma: esperado {esp['valor_esperado_soma']}, obteve {val}")

        # Registro sem valores de energia
        val = _obter_valor_total_mwh(esp["registro_vazio"])
        if val != esp["valor_esperado_vazio"]:
            erros.append(f"Registro vazio: esperado {esp['valor_esperado_vazio']}, obteve {val}")

        if erros:
            return nome, False, erros
        return nome, True, "Extracao de total MWh correta para todos os cenarios"
    except Exception as e:
        return nome, False, [str(e)]


def test_normalizar_energia():
    nome = "test_normalizar_energia"
    esp = ESPERADO[nome]
    try:
        df = _normalizar_grafico_energia_api(RESPOSTA_PRODUCAO_DIARIA, periodo="D")
        erros = []

        if len(df) < esp["min_linhas"]:
            erros.append(f"Esperava >= {esp['min_linhas']} linhas, obteve {len(df)}")

        if not df.empty and str(df.index.dtype) not in ("datetime64[ns]", "datetime64[us]"):
            erros.append(f"Index nao e datetime: {df.index.dtype}")

        # Verifica valores numericos
        for col in df.columns:
            if not all(isinstance(v, (int, float)) for v in df[col].values):
                erros.append(f"Coluna '{col}' tem valores nao numericos")

        if erros:
            return nome, False, erros
        return nome, True, f"{len(df)} linhas, colunas: {list(df.columns)}"
    except Exception as e:
        return nome, False, [str(e)]


def test_normalizar_nivel():
    nome = "test_normalizar_nivel"
    esp = ESPERADO[nome]
    try:
        df = _normalizar_grafico_nivel_api(RESPOSTA_NIVEL)
        erros = []

        if len(df) < esp["min_linhas"]:
            erros.append(f"Esperava >= {esp['min_linhas']} linhas, obteve {len(df)}")

        if not df.empty and str(df.index.dtype) not in ("datetime64[ns]", "datetime64[us]"):
            erros.append(f"Index nao e datetime: {df.index.dtype}")

        if erros:
            return nome, False, erros
        return nome, True, f"{len(df)} linhas, colunas: {list(df.columns)}"
    except Exception as e:
        return nome, False, [str(e)]


def test_normalizar_cards():
    nome = "test_normalizar_cards"
    esp = ESPERADO[nome]
    try:
        cards = _normalizar_cards_calculadora(RESPOSTA_PRODUCAO_MENSAL)
        erros = []

        if len(cards) < esp["min_cards"]:
            erros.append(f"Esperava >= {esp['min_cards']} cards, obteve {len(cards)}")

        for titulo, info in cards.items():
            for chave in esp["card_tem_chaves"]:
                if chave not in info:
                    erros.append(f"Card '{titulo}': chave '{chave}' ausente")

        if erros:
            return nome, False, erros
        return nome, True, f"{len(cards)} cards: {list(cards.keys())}"
    except Exception as e:
        return nome, False, [str(e)]


TODOS = [
    test_parse_data_periodo_dia,
    test_parse_data_periodo_hora,
    test_parse_data_periodo_mes,
    test_parse_data_formatos,
    test_parse_data_none,
    test_obter_valor_total_mwh,
    test_normalizar_energia,
    test_normalizar_nivel,
    test_normalizar_cards,
]
