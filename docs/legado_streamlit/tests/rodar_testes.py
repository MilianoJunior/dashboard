# -------------------------------------------------------------------
# FLUXO DO MODULO
# 1. rodar_etapa     -> Executa todos os testes de uma etapa e printa resultados
# 2. main            -> Roda todas as etapas em sequencia e exibe resumo final
# -------------------------------------------------------------------

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def rodar_etapa(nome_etapa, modulo):
    """Executa todos os testes de um modulo e retorna (passou, falhou, erros)."""
    print(f"\n{'='*60}")
    print(f"  ETAPA: {nome_etapa}")
    print(f"{'='*60}")

    passou = 0
    falhou = 0
    erros_etapa = []

    for fn_teste in modulo.TODOS:
        try:
            resultado = fn_teste()
            nome, sucesso, detalhe = resultado

            if sucesso:
                passou += 1
                print(f"  [OK]   {nome}")
                print(f"         {detalhe}")
            else:
                falhou += 1
                erros_etapa.append((nome, detalhe))
                print(f"  [ERRO] {nome}")
                if isinstance(detalhe, list):
                    for err in detalhe:
                        print(f"         - {err}")
                else:
                    print(f"         {detalhe}")
        except Exception as e:
            falhou += 1
            erros_etapa.append((fn_teste.__name__, [str(e)]))
            print(f"  [ERRO] {fn_teste.__name__}")
            print(f"         - Excecao nao tratada: {e}")

    print(f"\n  Resultado: {passou} OK, {falhou} ERRO")
    return passou, falhou, erros_etapa


def main():
    inicio = time.time()

    print("\n" + "#"*60)
    print("#  TESTES DO DASHBOARD ENGEGOM")
    print("#  " + time.strftime("%d/%m/%Y %H:%M:%S"))
    print("#"*60)

    etapas = [
        ("1 - Config Controller", "tests.test_config_controller"),
        ("2 - Calculos", "tests.test_calculos"),
        ("3 - API Controller", "tests.test_api_controller"),
        ("4 - Data Controller", "tests.test_data_controller"),
        ("5 - Componentes", "tests.test_componentes"),
        ("6 - Autenticacao", "tests.test_auth"),
    ]

    total_ok = 0
    total_erro = 0
    etapas_com_erro = []

    for nome_etapa, modulo_nome in etapas:
        try:
            modulo = __import__(modulo_nome, fromlist=["TODOS"])
            ok, erro, erros = rodar_etapa(nome_etapa, modulo)
            total_ok += ok
            total_erro += erro
            if erro > 0:
                etapas_com_erro.append((nome_etapa, erros))
        except Exception as e:
            total_erro += 1
            etapas_com_erro.append((nome_etapa, [("import", [str(e)])]))
            print(f"\n{'='*60}")
            print(f"  ETAPA: {nome_etapa}")
            print(f"{'='*60}")
            print(f"  [ERRO] Falha ao importar modulo: {e}")

    duracao = time.time() - inicio

    # Resumo final
    print(f"\n{'#'*60}")
    print(f"#  RESUMO FINAL")
    print(f"#{'─'*58}#")
    print(f"#  Total: {total_ok + total_erro} testes")
    print(f"#  OK:    {total_ok}")
    print(f"#  ERRO:  {total_erro}")
    print(f"#  Tempo: {duracao:.2f}s")
    print(f"#{'─'*58}#")

    if etapas_com_erro:
        print(f"#  ETAPAS COM FALHA:")
        for nome_etapa, erros in etapas_com_erro:
            print(f"#    - {nome_etapa}")
            for teste_nome, detalhes in erros:
                print(f"#      {teste_nome}: {detalhes}")
        print(f"#{'─'*58}#")
        print(f"#  RESULTADO: FALHOU")
    else:
        print(f"#  RESULTADO: TODOS PASSARAM")

    print(f"{'#'*60}\n")

    return total_erro == 0


if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)
