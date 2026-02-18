# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. _obter_codigo_usina_api         -> Resolve código da usina para payload da API
# 2. _parse_data_periodo             -> Parse de data com truncamento por periodo (H/D/M)
# 3. _obter_valor_total_mwh          -> Extrai valor total MWh de um registro da API
# 4. _consultar_producao_api         -> Consulta /producao-acumulada com periodo e datas
# 5. _consultar_nivel_api            -> Consulta /grupo-usina com grupo=hidraulica
# 6. _normalizar_grafico_energia_api -> Converte resposta em DataFrame p/ gráfico energia
# 7. _normalizar_grafico_nivel_api   -> Converte resposta em DataFrame p/ gráfico nível
# 8. _normalizar_cards_calculadora   -> Converte resposta mensal em list_cards
# 9. carregar_dados                  -> Atualiza session_state dos cards e gráficos
# 10. set_load_data                  -> Reseta flag de carregamento
# -------------------------------------------------------------------

import os
from datetime import datetime, timedelta

import streamlit as st
from dotenv import load_dotenv

import pandas as pd
from libs.controllers.api_controller import consultar_producao_acumulada_api, consultar_grupo_usina_api
from libs.models.datas import (
    get_db_data,
    get_grafico_energia,
    get_grafico_nivel,
    get_names_all_columns,
)
from libs.utils.decorators import desempenho, get_error

load_dotenv()

URL_API = (os.getenv("URL_API") or "").strip().rstrip("/")
API_TOKEN = (os.getenv("API_TOKEN") or "").strip()
MESES_PT = [
    "janeiro",
    "fevereiro",
    "marco",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]

def _parse_data_periodo(valor, periodo="D"):
    """Parse de data com truncamento adequado ao periodo:
    H -> preserva hora | D -> trunca para dia | M -> trunca para mes.
    """
    if not valor:
        return None

    if isinstance(valor, datetime):
        dt = valor
    else:
        texto = str(valor).strip()
        formatos = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%d/%m/%Y %H:%M",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%Y-%m",
        ]
        dt = None
        for fmt in formatos:
            try:
                dt = datetime.strptime(texto[:19], fmt)
                break
            except ValueError:
                continue
        if dt is None:
            return None

    if periodo == "H":
        return dt.replace(second=0, microsecond=0)
    if periodo == "M":
        return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)  # D



def _formatar_mes_ano(data_mes):
    return f"{MESES_PT[data_mes.month - 1]}/{data_mes.year}"


def _obter_valor_total_mwh(registro):
    chaves_prioritarias = ("total", "soma_total", "producao_total", "mwh_total")
    for chave in chaves_prioritarias:
        valor = registro.get(chave)
        if isinstance(valor, (int, float)):
            return float(valor)

    soma = 0.0
    encontrou = False
    for chave, valor in registro.items():
        if not isinstance(valor, (int, float)):
            continue
        chave_norm = str(chave).lower()
        if any(palavra in chave_norm for palavra in ("data", "periodo", "mes", "ano")):
            continue
        if any(palavra in chave_norm for palavra in ("prod", "producao", "energia", "mwh", "total")):
            soma += float(valor)
            encontrou = True
    if encontrou:
        return soma
    return None


def _obter_codigo_usina_api():
    codigo_em_sessao = st.session_state.get("usina_codigo_api")
    if codigo_em_sessao:
        return codigo_em_sessao

    usina_atual = st.session_state.get("usina", {})
    usinas_config = st.session_state.get("usinas", {})
    users_atual = usina_atual.get("users")

    for codigo, config_usina in usinas_config.items():
        if config_usina is usina_atual:
            st.session_state["usina_codigo_api"] = codigo
            return codigo
        if users_atual and config_usina.get("users") == users_atual:
            st.session_state["usina_codigo_api"] = codigo
            return codigo

    if users_atual:
        codigo_fallback = str(users_atual).upper()
        st.session_state["usina_codigo_api"] = codigo_fallback
        return codigo_fallback
    return None


def _consultar_producao_api(periodo="M", data_inicio=None, data_fim=None):
    codigo_usina = _obter_codigo_usina_api()
    if not codigo_usina:
        raise ValueError("Nao foi possivel resolver o codigo da usina da sessao")

    agora = datetime.now()
    if data_inicio is None:
        delta = timedelta(days=180) if periodo == "M" else timedelta(days=30)
        data_inicio = (agora - delta).strftime("%d/%m/%Y %H:%M")
    elif hasattr(data_inicio, "strftime"):
        data_inicio = data_inicio.strftime("%d/%m/%Y %H:%M")
    if data_fim is None:
        data_fim = agora.strftime("%d/%m/%Y %H:%M")
    elif hasattr(data_fim, "strftime"):
        data_fim = data_fim.strftime("%d/%m/%Y %H:%M")

    return consultar_producao_acumulada_api(
        url_api=URL_API,
        token_api=API_TOKEN,
        codigo_usina=codigo_usina,
        data_inicio=data_inicio,
        data_fim=data_fim,
        periodo=periodo,
    )


def _consultar_nivel_api(data_inicio=None, data_fim=None):
    codigo_usina = _obter_codigo_usina_api()
    if not codigo_usina:
        raise ValueError("Nao foi possivel resolver o codigo da usina da sessao")

    agora = datetime.now()
    if data_inicio is None:
        data_inicio = (agora - timedelta(days=30)).strftime("%d/%m/%Y %H:%M")
    elif hasattr(data_inicio, "strftime"):
        data_inicio = data_inicio.strftime("%d/%m/%Y %H:%M")
    if data_fim is None:
        data_fim = agora.strftime("%d/%m/%Y %H:%M")
    elif hasattr(data_fim, "strftime"):
        data_fim = data_fim.strftime("%d/%m/%Y %H:%M")

    return consultar_grupo_usina_api(
        url_api=URL_API,
        token_api=API_TOKEN,
        codigo_usina=codigo_usina,
        grupo="hidraulica",
        data_inicio=data_inicio,
        data_fim=data_fim,
    )


def _normalizar_grafico_nivel_api(resposta_api):
    """Converte resposta de /grupo-usina (hidraulica) em DataFrame com indice datetime."""
    dados = resposta_api.get("dados") or resposta_api.get("resultado") or []
    if not isinstance(dados, list) or not dados:
        return pd.DataFrame()

    registros = []
    for item in dados:
        if not isinstance(item, dict):
            continue
        data_raw = item.get("data_hora") or item.get("data")
        if not data_raw:
            continue
        dt = _parse_data_periodo(data_raw, "H")
        if dt is None:
            continue
        registro = {k: v for k, v in item.items() if k not in ("data_hora", "data")}
        registro["data_hora"] = dt
        registros.append(registro)

    if not registros:
        return pd.DataFrame()

    df = pd.DataFrame(registros).set_index("data_hora")
    df.index = pd.to_datetime(df.index)
    df = df.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    return df

def _normalizar_grafico_energia_api(resposta_api, periodo="D"):
    """Converte resposta da API em DataFrame com indice datetime.

    Colunas de energia ficam com nome original da API (ex: 'UG-01 Energia Acumulada').
    O grafico usa rename_colunas() para padronizar para 'UG-XX (MWh)'.
    """
    dados = resposta_api.get("resultado") or resposta_api.get("dados") or []
    if not isinstance(dados, list) or not dados:
        return pd.DataFrame()

    registros = []
    for item in dados:
        if not isinstance(item, dict):
            continue
        data_raw = item.get("data") or item.get("periodo") or item.get("data_hora")
        if not data_raw:
            continue
        dt = _parse_data_periodo(data_raw, periodo)
        if dt is None:
            continue
        registro = {
            k.removeprefix("prod_"): v
            for k, v in item.items()
            if k not in ("data", "periodo", "data_hora")
        }
        registro["data_hora"] = dt
        registros.append(registro)

    if not registros:
        return pd.DataFrame()

    df = pd.DataFrame(registros).set_index("data_hora")
    df.index = pd.to_datetime(df.index)
    df = df.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    return df


def _normalizar_cards_calculadora(resposta_api):
    dados = resposta_api.get("dados") or resposta_api.get("resultado") or []
    if not isinstance(dados, list) or not dados:
        return {}

    serie_mensal = []
    for registro in dados:
        if not isinstance(registro, dict):
            continue
        data_mes = _parse_data_periodo(
            registro.get("periodo")
            or registro.get("data_hora")
            or registro.get("data")
            or registro.get("mes")
            or registro.get("mes_ano")
            or registro.get("competencia"),
            "M",
        )
        valor_total = _obter_valor_total_mwh(registro)
        if data_mes is None or valor_total is None:
            continue
        serie_mensal.append((data_mes, round(float(valor_total), 2)))

    if not serie_mensal:
        return {}

    serie_mensal.sort(key=lambda item: item[0])
    cards_ordenados = []
    valor_anterior = None
    for data_mes, valor_atual in serie_mensal:
        percentual = None
        if valor_anterior not in (None, 0):
            percentual = round(((valor_atual - valor_anterior) / valor_anterior) * 100, 2)
        cards_ordenados.append(
            {
                "mes_label": _formatar_mes_ano(data_mes),
                "valor_mwh": valor_atual,
                "percentual": percentual,
            }
        )
        valor_anterior = valor_atual

    cards = {}
    data_consulta = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    for item in reversed(cards_ordenados):
        titulo = f"Geração - {item['mes_label']}".upper()
        cards[titulo] = {
            "value": item["valor_mwh"],
            "value_max": None,
            "value_min": None,
            "valor_real": None,
            "ano_anterior": None,
            "percentual": item["percentual"],
            "description": f"Mês {item['mes_label']}",
            "data_hora": data_consulta,
            "medida": "MWh",
        }
    return cards


@desempenho
def carregar_dados(periodo, data_inicial, data_final):
    import time
    try:
        print(f'periodo: {periodo}, data_inicial: {data_inicial}, data_final: {data_final}')
        list_cards_anterior = st.session_state.get("list_cards")
        if list_cards_anterior is None:
            print(f' 1 consulta: list_cards_anterior')
            try:
                inicio = time.time()
                print(' Testando consulta de cards')
                resposta_api = _consultar_producao_api(periodo="M")
                # print(f'resposta_api: {resposta_api}')
                # print(f' Tempo de consulta de cards: {time.time() - inicio:.4f} s')
                list_cards_novo = _normalizar_cards_calculadora(resposta_api)
                # print(f'list_cards_novo: {list_cards_novo}')
                fim = time.time()
                print(f'tempo: {fim - inicio:.4f} s')
                if list_cards_novo:
                    st.session_state.list_cards = list_cards_novo
                elif list_cards_anterior is None:
                    st.session_state.list_cards = {}
            except Exception as exc:
                if list_cards_anterior is None:
                    st.session_state.list_cards = {}
                st.warning("Falha ao carregar cards da API. Mantendo ultimo valor valido.")
                get_error("carregar_dados.cards_api", exc)
        else:
            print(f' 2 consulta: list_cards_anterior')

        grafico_anterior = st.session_state.get("grafico_energia")
        print(f'grafico_anterior: {grafico_anterior}')
        try:
            inicio = time.time()
            print(' Testando consulta de grafico')
            resposta_diaria = _consultar_producao_api(
                periodo=periodo or "D",
                data_inicio=data_inicial,
                data_fim=data_final,
            )
            # print(f' Tempo de consulta de grafico: {time.time() - inicio:.4f} s')
            # print(resposta_diaria)
            df_grafico = _normalizar_grafico_energia_api(resposta_diaria, periodo=periodo or "D")
            # print(df_grafico)
            fim = time.time()
            print(f'tempo: {fim - inicio:.4f} s')
            if not df_grafico.empty:
                st.session_state.grafico_energia = df_grafico
            elif grafico_anterior is None:
                st.session_state.grafico_energia = pd.DataFrame()
        except Exception as exc:
            if grafico_anterior is None:
                st.session_state.grafico_energia = pd.DataFrame()
            st.warning("Falha ao carregar grafico de energia da API. Mantendo ultimo valor valido.")
            get_error("carregar_dados.grafico_diario_api", exc)

        try:
            inicio = time.time()
            print(' Testando consulta de nivel')
            resposta_nivel = _consultar_nivel_api(data_inicio=data_inicial, data_fim=data_final)
            print(f' Tempo de consulta de nivel: {time.time() - inicio:.4f} s')
            df_nivel = _normalizar_grafico_nivel_api(resposta_nivel)
            # print(df_nivel)
            st.session_state.grafico_nivel = df_nivel if not df_nivel.empty else pd.DataFrame()
        except Exception as exc:
            if st.session_state.get("grafico_nivel") is None:
                st.session_state.grafico_nivel = pd.DataFrame()
            st.warning("Falha ao carregar grafico de nivel da API.")
            get_error("carregar_dados.grafico_nivel_api", exc)


    except Exception as exc:
        get_error("carregar_dados", exc)


@desempenho
def set_load_data():
    st.session_state.load_data = False
