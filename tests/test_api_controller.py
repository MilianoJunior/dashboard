# -------------------------------------------------------------------
# FLUXO DO MODULO
# 1. test_payload_producao       -> Payload montado corretamente
# 2. test_erro_sem_url           -> ValueError se URL_API vazio
# 3. test_erro_sem_token         -> ValueError se API_TOKEN vazio
# 4. test_erro_sem_usina         -> ValueError se codigo_usina vazio
# 5. test_post_json_sucesso      -> POST retorna JSON parseado
# 6. test_post_json_http_error   -> HTTPError vira RuntimeError
# -------------------------------------------------------------------

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import json
from unittest.mock import patch, MagicMock
from urllib import error

from libs.controllers.api_controller import (
    _montar_payload_producao_acumulada,
    consultar_producao_acumulada_api,
    consultar_grupo_usina_api,
    consultar_grupos_usina_api,
    consultar_sensor_usina_api,
    _post_json_sem_timeout,
)


ESPERADO = {
    "test_payload_producao": {
        "chaves": ["usina", "data_inicio", "data_fim", "periodo", "token"],
        "usina": "CGH-TESTE",
        "periodo": "D",
    },
    "test_erro_sem_url": {"excecao": ValueError},
    "test_erro_sem_token": {"excecao": ValueError},
    "test_erro_sem_usina": {"excecao": ValueError},
    "test_post_json_sucesso": {"retorno_tipo": dict},
    "test_post_json_http_error": {"excecao": RuntimeError},
}


def test_payload_producao():
    nome = "test_payload_producao"
    esp = ESPERADO[nome]
    try:
        payload = _montar_payload_producao_acumulada(
            codigo_usina="CGH-TESTE",
            data_inicio="01/03/2026 00:00",
            data_fim="31/03/2026 23:59",
            periodo="D",
            token_api="token123",
        )
        erros = []

        for chave in esp["chaves"]:
            if chave not in payload:
                erros.append(f"Chave '{chave}' ausente no payload")

        if payload.get("usina") != esp["usina"]:
            erros.append(f"Usina esperada '{esp['usina']}', obteve '{payload.get('usina')}'")

        if payload.get("periodo") != esp["periodo"]:
            erros.append(f"Periodo esperado '{esp['periodo']}', obteve '{payload.get('periodo')}'")

        if erros:
            return nome, False, erros
        return nome, True, f"Payload com chaves: {list(payload.keys())}"
    except Exception as e:
        return nome, False, [str(e)]


def test_erro_sem_url():
    nome = "test_erro_sem_url"
    try:
        consultar_producao_acumulada_api(
            url_api="", token_api="token", codigo_usina="CGH",
            data_inicio="01/01/2026", data_fim="31/01/2026",
        )
        return nome, False, ["Nao lancou excecao com URL vazia"]
    except ValueError:
        return nome, True, "ValueError lancado corretamente"
    except Exception as e:
        return nome, False, [f"Excecao errada: {type(e).__name__}: {e}"]


def test_erro_sem_token():
    nome = "test_erro_sem_token"
    try:
        consultar_producao_acumulada_api(
            url_api="http://api.teste", token_api="", codigo_usina="CGH",
            data_inicio="01/01/2026", data_fim="31/01/2026",
        )
        return nome, False, ["Nao lancou excecao com token vazio"]
    except ValueError:
        return nome, True, "ValueError lancado corretamente"
    except Exception as e:
        return nome, False, [f"Excecao errada: {type(e).__name__}: {e}"]


def test_erro_sem_usina():
    nome = "test_erro_sem_usina"
    try:
        consultar_producao_acumulada_api(
            url_api="http://api.teste", token_api="token", codigo_usina="",
            data_inicio="01/01/2026", data_fim="31/01/2026",
        )
        return nome, False, ["Nao lancou excecao com usina vazia"]
    except ValueError:
        return nome, True, "ValueError lancado corretamente"
    except Exception as e:
        return nome, False, [f"Excecao errada: {type(e).__name__}: {e}"]


def test_post_json_sucesso():
    nome = "test_post_json_sucesso"
    try:
        resposta_simulada = {"resultado": [{"total": 100.5}]}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(resposta_simulada).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("libs.controllers.api_controller.request.urlopen", return_value=mock_response):
            resultado = _post_json_sem_timeout("http://api.teste/endpoint", {"chave": "valor"})

        erros = []
        if not isinstance(resultado, dict):
            erros.append(f"Tipo esperado dict, obteve {type(resultado)}")
        if resultado != resposta_simulada:
            erros.append(f"Resposta diferente do esperado")

        if erros:
            return nome, False, erros
        return nome, True, f"POST retornou: {resultado}"
    except Exception as e:
        return nome, False, [str(e)]


def test_post_json_http_error():
    nome = "test_post_json_http_error"
    try:
        mock_exc = error.HTTPError(
            url="http://api.teste",
            code=500,
            msg="Internal Server Error",
            hdrs=None,
            fp=MagicMock(read=MagicMock(return_value=b"erro interno")),
        )

        with patch("libs.controllers.api_controller.request.urlopen", side_effect=mock_exc):
            _post_json_sem_timeout("http://api.teste/endpoint", {"chave": "valor"})

        return nome, False, ["Nao lancou excecao para HTTP 500"]
    except RuntimeError as e:
        if "500" in str(e):
            return nome, True, f"RuntimeError lancado: {e}"
        return nome, False, [f"RuntimeError sem codigo 500: {e}"]
    except Exception as e:
        return nome, False, [f"Excecao errada: {type(e).__name__}: {e}"]


TODOS = [
    test_payload_producao,
    test_erro_sem_url,
    test_erro_sem_token,
    test_erro_sem_usina,
    test_post_json_sucesso,
    test_post_json_http_error,
]
