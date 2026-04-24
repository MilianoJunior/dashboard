# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. parse_report_params          -> Valida parametros da tela de relatorios
# 2. listar_anos_relatorio        -> Monta opcoes de ano para o formulario
# 3. _montar_dados_vazao          -> Consulta vazao horaria apenas para PCH-PIRA
# 4. montar_dados_relatorio       -> Consulta API historica e monta dados premium
# 5. gerar_pdf_relatorio          -> Renderiza PDF em arquivo temporario
# -------------------------------------------------------------------

import calendar
import os
import tempfile
from datetime import datetime

from libs.models.consultas import (
    carregar_config_usina,
    consultar_nivel,
    consultar_producao,
    normalizar_energia,
)
from libs.utils.decorators import desempenho
from libs.utils.gerar_pdf_v2 import MESES_TODOS, gerar_relatorio


CLIENTE_PADRAO = "ENGESEP O&M"
UNIDADE_CONSUMIDORA_PADRAO = "N/D"
USINA_COM_VAZAO = "PCH-PIRA"
LEITURAS_VAZAO_DIA = 24


def listar_anos_relatorio(quantidade=5):
    ano_atual = datetime.now().year
    return list(range(ano_atual, ano_atual - quantidade, -1))


def parse_report_params(parametros=None):
    parametros = parametros or {}
    anos_validos = listar_anos_relatorio()
    ano_atual = anos_validos[0]

    try:
        ano = int(parametros.get("ano", ano_atual))
    except (TypeError, ValueError):
        ano = ano_atual

    if ano < 2020 or ano > ano_atual + 1:
        ano = ano_atual

    return {"ano": ano}


def _formatar_periodo(ano):
    return f"01/01/{ano} - 31/12/{ano}"


def _periodo_api(ano):
    return (
        datetime(ano, 1, 1, 0, 0),
        datetime(ano, 12, 31, 23, 59, 59),
    )


def _capacidade_instalada_kw(codigo_usina):
    config = carregar_config_usina(codigo_usina)
    dispositivos = config.get("dispositivos", {})

    total_kw = 0.0
    for dispositivo in dispositivos.values():
        caracteristicas = dispositivo.get("caracteristicas", {})
        total_kw += float(caracteristicas.get("potência máxima", 0) or 0)
    return total_kw


def _meta_diaria_mwh(codigo_usina):
    capacidade_kw = _capacidade_instalada_kw(codigo_usina)
    if capacidade_kw <= 0:
        return 0.0
    return round(capacidade_kw * 24 / 1000, 2)


def _dias_no_mes(ano, mes_idx):
    return calendar.monthrange(ano, mes_idx)[1]


def _inicializar_geracao_anual():
    return {mes: [0.0] * 31 for mes in MESES_TODOS}


def _somar_geracao_diaria(df):
    if df.empty:
        return {}

    df_diario = df.copy()
    df_diario["total_mwh"] = df_diario.sum(axis=1)
    serie = df_diario["total_mwh"].groupby(df_diario.index.date).sum()
    return {data: round(float(valor), 2) for data, valor in serie.items()}


def _parse_data_historica(valor):
    if not valor:
        return None

    texto = str(valor).strip()
    formatos = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M",
    ]
    for formato in formatos:
        try:
            return datetime.strptime(texto[:19], formato)
        except ValueError:
            continue
    return None


def _to_float(valor):
    if valor is None or valor == "":
        return None
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _extrair_leituras_vazao(resposta_api):
    dados = resposta_api.get("dados") or resposta_api.get("resultado") or []
    leituras = []

    for item in dados:
        if not isinstance(item, dict):
            continue

        data_hora = _parse_data_historica(item.get("data_hora") or item.get("data"))
        if data_hora is None:
            continue

        valores = []
        for chave, valor in item.items():
            chave_norm = str(chave).lower()
            if "vazão" not in chave_norm and "vazao" not in chave_norm:
                continue
            numero = _to_float(valor)
            if numero is not None:
                valores.append(numero)

        if valores:
            leituras.append({
                "data_hora": data_hora,
                "valor": round(sum(valores), 2),
            })

    return sorted(leituras, key=lambda item: item["data_hora"])


def _inicializar_matriz_vazao():
    return {
        "media_diaria": {mes: [0.0] * 31 for mes in MESES_TODOS},
        "leituras_diarias": {mes: [0] * 31 for mes in MESES_TODOS},
    }


def _montar_vazao_diaria(ano, leituras):
    matriz = _inicializar_matriz_vazao()
    por_dia = {}

    for leitura in leituras:
        data = leitura["data_hora"].date()
        if data.year != ano:
            continue
        por_dia.setdefault(data, []).append(leitura["valor"])

    for data, valores in por_dia.items():
        mes = MESES_TODOS[data.month - 1]
        idx = data.day - 1
        matriz["media_diaria"][mes][idx] = round(sum(valores) / len(valores), 2)
        matriz["leituras_diarias"][mes][idx] = len(valores)

    return matriz


def _montar_dados_vazao(codigo_usina, ano, data_inicio, data_fim):
    if codigo_usina != USINA_COM_VAZAO:
        return None

    resposta = consultar_nivel(
        codigo_usina=codigo_usina,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )
    leituras = _extrair_leituras_vazao(resposta)
    matriz = _montar_vazao_diaria(ano, leituras)
    valores = [leitura["valor"] for leitura in leituras]

    if not valores:
        return {
            "disponivel": False,
            "motivo": "Sem leituras de vazao no periodo selecionado.",
            **matriz,
        }

    maxima = max(leituras, key=lambda item: item["valor"])
    minima = min(leituras, key=lambda item: item["valor"])
    dias_com_dados = sum(
        1
        for mes in MESES_TODOS
        for quantidade in matriz["leituras_diarias"][mes]
        if quantidade > 0
    )

    return {
        "disponivel": True,
        "unidade": "m3/s",
        "leituras_total": len(leituras),
        "leituras_por_dia_esperadas": LEITURAS_VAZAO_DIA,
        "dias_com_dados": dias_com_dados,
        "media_anual": round(sum(valores) / len(valores), 2),
        "maxima": round(maxima["valor"], 2),
        "maxima_data": maxima["data_hora"].strftime("%d/%m/%Y %H:%M"),
        "minima": round(minima["valor"], 2),
        "minima_data": minima["data_hora"].strftime("%d/%m/%Y %H:%M"),
        **matriz,
    }


def _montar_matriz_geracao(ano, totais_por_dia):
    geracao = _inicializar_geracao_anual()

    for data, valor in totais_por_dia.items():
        if data.year != ano:
            continue
        mes = MESES_TODOS[data.month - 1]
        geracao[mes][data.day - 1] = valor

    return geracao


def _montar_referencia_mensal(ano, meta_diaria_mwh):
    referencia = {}
    for mes_idx, mes in enumerate(MESES_TODOS, start=1):
        referencia[mes] = round(meta_diaria_mwh * _dias_no_mes(ano, mes_idx), 2)
    return referencia


def _calcular_resumo(geracao, referencia, meta_diaria_mwh):
    totais = {mes: round(sum(valores), 2) for mes, valores in geracao.items()}
    perf = {
        mes: round(totais[mes] / referencia[mes] * 100, 1)
        if referencia.get(mes)
        else 0.0
        for mes in MESES_TODOS
    }

    meses_op = [mes for mes in MESES_TODOS if totais.get(mes, 0) > 0]
    geracao_anual = round(sum(totais.values()), 2)
    referencia_anual = round(sum(referencia.values()), 2)
    pico_mes = max(meses_op, key=lambda mes: totais[mes]) if meses_op else "-"

    dias_operados = sum(1 for mes in meses_op for valor in geracao[mes] if valor > 0)
    dias_acima_meta = sum(
        1
        for mes in meses_op
        for valor in geracao[mes]
        if meta_diaria_mwh > 0 and valor >= meta_diaria_mwh
    )

    return {
        "totais": totais,
        "perf": perf,
        "meses_op": meses_op,
        "resumo": {
            "anual": geracao_anual,
            "gf_anual": referencia_anual,
            "perf_global": round(geracao_anual / referencia_anual * 100, 1)
            if referencia_anual
            else 0.0,
            "media": round(geracao_anual / len(meses_op), 2) if meses_op else 0.0,
            "pico_mes": pico_mes,
            "pico_val": totais.get(pico_mes, 0),
            "dias_acima_meta": dias_acima_meta,
            "dias_operados": dias_operados,
        },
    }


@desempenho
def montar_dados_relatorio(codigo_usina, ano):
    data_inicio, data_fim = _periodo_api(ano)
    resposta = consultar_producao(
        periodo="D",
        data_inicio=data_inicio,
        data_fim=data_fim,
        codigo_usina=codigo_usina,
    )
    df = normalizar_energia(resposta, periodo="D")

    meta_diaria = _meta_diaria_mwh(codigo_usina)
    geracao = _montar_matriz_geracao(ano, _somar_geracao_diaria(df))
    referencia = _montar_referencia_mensal(ano, meta_diaria)
    calculos = _calcular_resumo(geracao, referencia, meta_diaria)
    vazao = _montar_dados_vazao(codigo_usina, ano, data_inicio, data_fim)

    return {
        "meta": {
            "ano": str(ano),
            "cliente": CLIENTE_PADRAO,
            "usina": codigo_usina,
            "uc": UNIDADE_CONSUMIDORA_PADRAO,
            "periodo": _formatar_periodo(ano),
            "emissao": datetime.now().strftime("%d/%m/%Y"),
            "meta_dia": meta_diaria,
            "gf_mwh": meta_diaria,
        },
        "geracao": geracao,
        "gf": referencia,
        "vazao": vazao,
        **calculos,
    }


@desempenho
def gerar_pdf_relatorio(codigo_usina, ano):
    dados = montar_dados_relatorio(codigo_usina=codigo_usina, ano=ano)
    nome_arquivo = f"relatorio_{codigo_usina}_{ano}.pdf".replace("/", "-")
    destino = os.path.join(tempfile.gettempdir(), nome_arquivo)
    gerar_relatorio(destino, dados=dados)
    return destino, nome_arquivo
