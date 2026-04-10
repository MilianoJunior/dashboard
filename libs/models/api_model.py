# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. iniciar_rastreio_api               -> Reseta contadores por requisição
# 2. imprimir_resumo_api                -> Imprime totais da rodada no terminal
# 3. _montar_payload_producao_acumulada -> Monta payload padrão da API
# 4. _post_json_sem_timeout             -> POST JSON com logging detalhado
# 5. _get_json_sem_timeout              -> GET JSON com logging detalhado
# 6. consultar_producao_acumulada_api   -> Consulta produção acumulada por período
# 7. consultar_grupo_usina_api          -> Consulta variáveis de um grupo da usina
# 8. consultar_grupos_usina_api         -> Lista grupos e variáveis disponíveis
# 9. consultar_sensor_usina_api         -> Consulta histórico de uma variável
# -------------------------------------------------------------------

import json
import time
from urllib import error, request

from libs.utils.decorators import desempenho

_api_stats = {
    "chamadas": 0,
    "bytes": 0,
    "registros": 0,
    "tempo_s": 0.0,
    "erros": 0,
}


def iniciar_rastreio_api():
    """Reseta contadores para rastrear uma nova rodada de chamadas."""
    _api_stats.update(chamadas=0, bytes=0, registros=0, tempo_s=0.0, erros=0)


def imprimir_resumo_api():
    """Imprime totais acumulados da rodada no terminal."""
    s = _api_stats
    print(
        f"\n{'=' * 70}\n"
        f"[API-HIST RESUMO] {s['chamadas']} chamadas | "
        f"{s['tempo_s']:.2f}s total | "
        f"{s['bytes']:,} bytes | "
        f"{s['registros']} registros | "
        f"{s['erros']} erros"
        f"\n{'=' * 70}",
        flush=True,
    )


def _resumir_payload(payload):
    """Extrai info relevante do payload para log (sem token)."""
    parts = []
    if payload.get("usina"):
        parts.append(payload["usina"])
    di, df = payload.get("data_inicio", ""), payload.get("data_fim", "")
    if di and df:
        parts.append(f"{di} → {df}")
    if payload.get("periodo"):
        parts.append(f"periodo={payload['periodo']}")
    if payload.get("grupo"):
        parts.append(f"grupo={payload['grupo']}")
    return " | ".join(parts)


def _contar_registros(resultado):
    """Conta registros na resposta (chave 'resultado' ou 'dados')."""
    dados = resultado.get("resultado") or resultado.get("dados") or []
    return len(dados) if isinstance(dados, list) else 0


def _montar_payload_producao_acumulada(codigo_usina, data_inicio, data_fim, periodo, token_api):
    return {
        "usina": codigo_usina,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "periodo": periodo,
        "token": token_api,
    }


def _post_json_sem_timeout(url, payload):
    _api_stats["chamadas"] += 1
    num = _api_stats["chamadas"]
    endpoint = url.rsplit("/", 1)[-1]
    contexto = _resumir_payload(payload)

    inicio = time.perf_counter()
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req) as resp:
            raw = resp.read()
            tempo = time.perf_counter() - inicio
            resultado = json.loads(raw.decode("utf-8"))

            n_bytes = len(raw)
            n_regs = _contar_registros(resultado)

            _api_stats["bytes"] += n_bytes
            _api_stats["registros"] += n_regs
            _api_stats["tempo_s"] += tempo

            print(
                f"[API-HIST #{num}] {endpoint} | {contexto} "
                f"-> {tempo:.3f}s | {n_bytes:,} bytes | {n_regs} registros",
                flush=True,
            )
            return resultado

    except error.HTTPError as exc:
        tempo = time.perf_counter() - inicio
        _api_stats["erros"] += 1
        _api_stats["tempo_s"] += tempo
        detalhe = exc.read().decode("utf-8", errors="ignore")
        print(
            f"[API-HIST #{num}] {endpoint} | {contexto} "
            f"-> ERRO HTTP {exc.code} em {tempo:.3f}s",
            flush=True,
        )
        raise RuntimeError(f"API retornou HTTP {exc.code}: {detalhe}") from exc

    except error.URLError as exc:
        tempo = time.perf_counter() - inicio
        _api_stats["erros"] += 1
        _api_stats["tempo_s"] += tempo
        print(
            f"[API-HIST #{num}] {endpoint} | {contexto} "
            f"-> FALHA CONEXÃO em {tempo:.3f}s | {exc.reason}",
            flush=True,
        )
        raise RuntimeError(f"Falha de conexao com API: {exc.reason}") from exc


def _get_json_sem_timeout(url):
    _api_stats["chamadas"] += 1
    num = _api_stats["chamadas"]
    endpoint = url.rsplit("/", 1)[-1]

    inicio = time.perf_counter()
    req = request.Request(url, method="GET")
    try:
        with request.urlopen(req) as resp:
            raw = resp.read()
            tempo = time.perf_counter() - inicio
            resultado = json.loads(raw.decode("utf-8"))

            n_bytes = len(raw)
            n_regs = _contar_registros(resultado)

            _api_stats["bytes"] += n_bytes
            _api_stats["registros"] += n_regs
            _api_stats["tempo_s"] += tempo

            print(
                f"[API-HIST #{num}] GET {endpoint} "
                f"-> {tempo:.3f}s | {n_bytes:,} bytes | {n_regs} registros",
                flush=True,
            )
            return resultado

    except error.HTTPError as exc:
        tempo = time.perf_counter() - inicio
        _api_stats["erros"] += 1
        _api_stats["tempo_s"] += tempo
        detalhe = exc.read().decode("utf-8", errors="ignore")
        print(
            f"[API-HIST #{num}] GET {endpoint} "
            f"-> ERRO HTTP {exc.code} em {tempo:.3f}s",
            flush=True,
        )
        raise RuntimeError(f"API retornou HTTP {exc.code}: {detalhe}") from exc

    except error.URLError as exc:
        tempo = time.perf_counter() - inicio
        _api_stats["erros"] += 1
        _api_stats["tempo_s"] += tempo
        print(
            f"[API-HIST #{num}] GET {endpoint} "
            f"-> FALHA CONEXÃO em {tempo:.3f}s | {exc.reason}",
            flush=True,
        )
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
