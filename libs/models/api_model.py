# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. _montar_payload_producao_acumulada -> Monta payload padrão da API
# 2. _post_json_sem_timeout             -> Executa POST JSON sem timeout explícito
# 3. _get_json_sem_timeout              -> Executa GET JSON sem timeout explícito
# 4. consultar_producao_acumulada_api   -> Consulta produção acumulada por período
# 5. consultar_grupo_usina_api          -> Consulta variáveis de um grupo da usina
# 6. consultar_grupos_usina_api         -> Lista grupos e variáveis disponíveis
# 7. consultar_sensor_usina_api         -> Consulta histórico de uma variável
# -------------------------------------------------------------------

import json
from urllib import error, request
from libs.utils.decorators import desempenho
cont_conexao = 0


def _montar_payload_producao_acumulada(codigo_usina, data_inicio, data_fim, periodo, token_api):
    return {
        "usina": codigo_usina,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "periodo": periodo,
        "token": token_api,
    }


@desempenho
def _post_json_sem_timeout(url, payload):
    global cont_conexao
    cont_conexao += 1
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:

        with request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detalhe = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"API retornou HTTP {exc.code}: {detalhe}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Falha de conexao com API: {exc.reason}") from exc


@desempenho
def consultar_producao_acumulada_api(url_api, token_api, codigo_usina, data_inicio, data_fim, periodo="M"):
    if not url_api:
        raise ValueError("URL_API nao configurada no .env")
    if not token_api:
        raise ValueError("API_TOKEN nao configurado no .env")
    if not codigo_usina:
        raise ValueError("Codigo da usina nao informado")

    payload = _montar_payload_producao_acumulada(
        codigo_usina=codigo_usina,
        data_inicio=data_inicio,
        data_fim=data_fim,
        periodo=periodo,
        token_api=token_api,
    )
    return _post_json_sem_timeout(f"{url_api}/producao-acumulada", payload)


@desempenho
def consultar_grupo_usina_api(url_api, token_api, codigo_usina, grupo, data_inicio, data_fim):
    if not url_api:
        raise ValueError("URL_API nao configurada no .env")
    if not token_api:
        raise ValueError("API_TOKEN nao configurado no .env")
    if not codigo_usina:
        raise ValueError("Codigo da usina nao informado")

    payload = {
        "usina": codigo_usina,
        "grupo": grupo,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "token": token_api,
    }
    return _post_json_sem_timeout(f"{url_api}/grupo-usina", payload)


@desempenho
def _get_json_sem_timeout(url):
    global cont_conexao
    cont_conexao += 1
    req = request.Request(url, method="GET")
    try:
        with request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detalhe = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"API retornou HTTP {exc.code}: {detalhe}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Falha de conexao com API: {exc.reason}") from exc


@desempenho
def consultar_grupos_usina_api(url_api, codigo_usina):
    if not url_api:
        raise ValueError("URL_API nao configurada no .env")
    if not codigo_usina:
        raise ValueError("Codigo da usina nao informado")
    return _get_json_sem_timeout(f"{url_api}/grupos/{codigo_usina}")


@desempenho
def consultar_sensor_usina_api(url_api, token_api, codigo_usina, variavel, data_inicio, data_fim):
    if not url_api:
        raise ValueError("URL_API nao configurada no .env")
    if not token_api:
        raise ValueError("API_TOKEN nao configurado no .env")
    if not codigo_usina:
        raise ValueError("Codigo da usina nao informado")

    payload = {
        "usina": codigo_usina,
        "variavel": variavel,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "token": token_api,
    }
    return _post_json_sem_timeout(f"{url_api}/sensor-usina", payload)
