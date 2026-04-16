# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. _agora_log                -> Formata timestamp das mensagens
# 2. _eh_chave_sensivel        -> Mascara argumentos sensíveis
# 3. _resumir_valor            -> Compacta valores para log
# 4. _resumir_argumentos       -> Resume args/kwargs com nomes dos parâmetros
# 5. _obter_contexto_execucao  -> Detecta contexto Flask atual
# 6. _log_desempenho           -> Emite linha padronizada de rastreio
# 7. desempenho                -> Decorator de início/fim/erro com tempo
# 8. _formatar_erro            -> Gera mensagem detalhada de exceção
# 9. get_error_cached          -> Loga erro e relança exceção
# 10. get_error                -> Loga erro e tenta refletir no Streamlit
# -------------------------------------------------------------------

from contextvars import ContextVar
from datetime import date, datetime
from functools import wraps
from itertools import count
import inspect
import traceback
import time

_CONTADOR_CHAMADAS = count(1)
_NIVEL_CHAMADA = ContextVar("nivel_chamada_desempenho", default=0)
_CHAVES_SENSIVEIS = ("token", "password", "senha", "secret", "authorization")


def _agora_log():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def _eh_chave_sensivel(nome_campo):
    nome_normalizado = str(nome_campo or "").lower()
    return any(chave in nome_normalizado for chave in _CHAVES_SENSIVEIS)


def _resumir_valor(valor, nome_campo=None):
    if _eh_chave_sensivel(nome_campo):
        return "<oculto>"

    if valor is None:
        return "None"

    if isinstance(valor, bool):
        return str(valor)

    if isinstance(valor, (int, float)):
        return repr(valor)

    if isinstance(valor, (datetime, date)):
        return valor.isoformat()

    if isinstance(valor, str):
        texto = valor.strip()
        if len(texto) > 40:
            texto = f"{texto[:37]}..."
        return repr(texto)

    if isinstance(valor, dict):
        chaves = list(valor.keys())[:5]
        return f"dict(keys={chaves}, len={len(valor)})"

    if isinstance(valor, (list, tuple, set)):
        return f"{type(valor).__name__}(len={len(valor)})"

    shape = getattr(valor, "shape", None)
    if shape is not None:
        return f"{type(valor).__name__}(shape={shape})"

    return type(valor).__name__


def _resumir_argumentos(funcao, *args, **kwargs):
    try:
        assinatura = inspect.signature(funcao)
        vinculados = assinatura.bind_partial(*args, **kwargs)
        pares = []
        for nome, valor in vinculados.arguments.items():
            if nome == "self":
                continue
            pares.append(f"{nome}={_resumir_valor(valor, nome)}")
        return ", ".join(pares) if pares else "sem-args"
    except Exception:
        return f"args={len(args)} kwargs={len(kwargs)}"


def _obter_contexto_execucao():
    try:
        from flask import has_request_context, request

        if has_request_context():
            return f"{request.method} {request.path}"
    except Exception:
        pass
    return "fora-flask"


def _log_desempenho(evento, chamada_id, nivel, nome_completo, contexto, detalhe, detalhe2=None):
    identacao = "  " * nivel
    detalhe2 = f" | {detalhe2}" if detalhe2 else ""
    print(
        f"[{_agora_log()}] [PERF {chamada_id:04d}] {identacao}{evento} "
        f"{nome_completo} {detalhe2}",
        flush=True,
    )


def desempenho(funcao):
    @wraps(funcao)
    def wrapper(*args, **kwargs):
        chamada_id = next(_CONTADOR_CHAMADAS)
        nivel_atual = _NIVEL_CHAMADA.get()
        nome_completo = f"{funcao.__module__}.{funcao.__name__}"
        contexto = _obter_contexto_execucao()
        args_resumidos = _resumir_argumentos(funcao, *args, **kwargs)

        # _log_desempenho("->", chamada_id, nivel_atual, nome_completo, contexto, f"args: {args_resumidos}",None)

        token_nivel = _NIVEL_CHAMADA.set(nivel_atual + 1)
        inicio = time.perf_counter()

        try:
            resultado = funcao(*args, **kwargs)
            tempo_total = time.perf_counter() - inicio
            retorno_resumido = _resumir_valor(resultado, "retorno")
            # _log_desempenho(
            #     "<-",
            #     chamada_id,
            #     nivel_atual,
            #     nome_completo,
            #     contexto,
            #     f"tempo={tempo_total:.4f}s | retorno: {retorno_resumido}",
            #     f"tempo={tempo_total:.4f}s",
            # )
            return resultado
        except Exception as erro:
            tempo_total = time.perf_counter() - inicio
            _log_desempenho(
                "!!",
                chamada_id,
                nivel_atual,
                nome_completo,
                contexto,
                f"tempo={tempo_total:.4f}s | erro: {type(erro).__name__}: {erro}",
            )
            raise
        finally:
            _NIVEL_CHAMADA.reset(token_nivel)

    return wrapper


def _formatar_erro(name, erro):
    traceback_info = traceback.extract_tb(erro.__traceback__)
    if traceback_info:
        ultimo_frame = traceback_info[-1]
        origem = (
            f"{ultimo_frame.filename.split('/')[-1]}:"
            f"{ultimo_frame.lineno} em {ultimo_frame.name}"
        )
    else:
        origem = "origem-desconhecida"

    return (
        f"Erro em {name} | {type(erro).__name__}: {erro} | "
        f"origem={origem}"
    )


def get_error_cached(name, erro: Exception) -> str:
    mensagem = _formatar_erro(name, erro)
    print(f"[{_agora_log()}] [ERROR CACHED] {mensagem}", flush=True)
    raise erro


def get_error(name, erro: Exception) -> str:
    mensagem = _formatar_erro(name, erro)
    print(f"[{_agora_log()}] [ERROR] {mensagem}", flush=True)

    try:
        import streamlit as st
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        if get_script_run_ctx() is not None:
            st.error(mensagem)
    except Exception:
        pass

    return mensagem
