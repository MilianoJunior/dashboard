# -------------------------------------------------------------------
# Funções de consulta e normalização desacopladas do Streamlit.
# Reutilizáveis tanto pelo Flask (dashboard.py) quanto pelo Streamlit
# (data_controller.py).
#
# FLUXO:
# 1. consultar_producao  -> Consulta /producao-acumulada com periodo e datas
# 2. consultar_nivel     -> Consulta /grupo-usina com grupo=hidraulica
# 3. normalizar_energia  -> Converte resposta em DataFrame p/ gráfico energia
# 4. normalizar_nivel    -> Converte resposta em DataFrame p/ gráfico nível
# -------------------------------------------------------------------

import json
import os
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv

from libs.controllers.api_controller import (
    consultar_producao_acumulada_api,
    consultar_grupo_usina_api,
)
from libs.utils.decorators import desempenho

load_dotenv()

URL_API = (os.getenv("URL_API") or "").strip().rstrip("/")
API_TOKEN = (os.getenv("API_TOKEN") or "").strip()

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'usinas_dispositivos.json')
_config_cache = None


@desempenho
def carregar_config_usina(codigo_usina):
    """Carrega config da usina do JSON. Mapeia 'PCH-PIRA' -> 'PCH PIRA'."""
    global _config_cache
    if _config_cache is None:
        with open(_CONFIG_PATH, 'r', encoding='utf-8') as f:
            _config_cache = json.load(f)
    # A chave no JSON usa espaço em vez de hífen: "PCH PIRA" vs "PCH-PIRA"
    chave = codigo_usina.replace('-', ' ')
    return _config_cache.get(chave, {})


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


@desempenho
def consultar_producao(periodo="M", data_inicio=None, data_fim=None, codigo_usina=None):
    """Consulta /producao-acumulada. Equivale a _consultar_producao_api do data_controller."""
    if not codigo_usina:
        raise ValueError("codigo_usina é obrigatório")

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


@desempenho
def consultar_nivel(data_inicio=None, data_fim=None, codigo_usina=None):
    """Consulta /grupo-usina com grupo=hidraulica. Equivale a _consultar_nivel_api."""
    if not codigo_usina:
        raise ValueError("codigo_usina é obrigatório")

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


@desempenho
def normalizar_energia(resposta_api, periodo="D"):
    """Converte resposta da API em DataFrame com indice datetime.
    Equivale a _normalizar_grafico_energia_api do data_controller.
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

    for col in df.columns:
        if df[col].dtype == object or df[col].dtype.name == 'string':
            df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
        df[col] = pd.to_numeric(df[col], errors="coerce").round(2)

    # Excluir coluna se tiver >= 30% de Nones (exige 70% de dados não-nulos)
    limite = int(len(df) * 0.7)
    df = df.dropna(thresh=limite, axis=1)
    
    # Preencher restantes com o anterior, e preencher qualquer sobra inicial com 0.0
    df = df.ffill().fillna(0.0)
    return df


@desempenho
def normalizar_nivel(resposta_api):
    """Converte resposta de /grupo-usina (hidraulica) em DataFrame com indice datetime.
    Equivale a _normalizar_grafico_nivel_api do data_controller.
    """
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

    for col in df.columns:
        if df[col].dtype == object or df[col].dtype.name == 'string':
            df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
        df[col] = pd.to_numeric(df[col], errors="coerce").round(2)

    # Excluir coluna se tiver >= 30% de Nones (exige 70% de dados não-nulos)
    limite = int(len(df) * 0.7)
    df = df.dropna(thresh=limite, axis=1)
    
    # Preencher restantes com o anterior, e preencher qualquer sobra inicial com 0.0
    df = df.ffill().fillna(0.0)
    return df
