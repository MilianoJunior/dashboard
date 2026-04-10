# -------------------------------------------------------------------
# TESTE DE INTEGRACAO — Leitura em Tempo Real via API Modbus
#
# Verifica se o ciclo completo de leitura de uma usina (todas as UGs
# + nivel montante) responde corretamente e dentro do limite de 20s.
#
# Uso:
#   pytest tests/test_integracao_rt.py -v -s
#   python tests/test_integracao_rt.py            # execucao direta
# -------------------------------------------------------------------

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from libs.views.servicos.connect import _ler_gauges_usina, _carregar_config
from libs.models.gauge_rt import montar_registros_gauge, dispositivo_tem_gauge

LIMITE_CICLO_SEGUNDOS = 20.0
LIMITE_LEITURA_INDIVIDUAL = 5.0

USINAS_PARA_TESTAR = [
    "PCH-PIRA",
    "CGH-APARECIDA",
    "CGH-FAE",
    "CGH-HOPPEN",
    "CGH-PICADAS-ALTAS",
    "PCH-PEDRAS",
]


# ── helpers de formatacao ──────────────────────────────────────────

def _barra(percent, largura=20):
    preenchido = round(largura * percent / 100)
    return f"[{'█' * preenchido}{'░' * (largura - preenchido)}]"


def _cor_status(status):
    mapa = {
        "US": "🟢",
        "UMD": "🟡",
        "UPS": "🟠",
        "UPGM": "🔵",
        "UP": "🔴",
        "Offline": "⚫",
        "SEM STATUS": "⚪",
    }
    return mapa.get(status, "❓")


def _formatar_resultado_ciclo(codigo_usina, usinas, resumo_rt, tempo_total, tempos_individuais):
    """Formata o resultado de um ciclo de leitura em tabela legivel."""
    linhas = []
    linhas.append("")
    linhas.append(f"{'═' * 70}")
    linhas.append(f"  USINA: {codigo_usina}")
    linhas.append(f"  Tempo total do ciclo: {tempo_total:.3f}s  (limite: {LIMITE_CICLO_SEGUNDOS}s)")
    linhas.append(f"  Leituras: {len(tempos_individuais)} requisicoes")
    linhas.append(f"{'─' * 70}")

    # Tabela de UGs
    linhas.append(f"  {'Dispositivo':<20} {'Status':<12} {'Potencia':>12} {'Max':>10} {'%':>6} {'Tempo':>8}")
    linhas.append(f"  {'─' * 20} {'─' * 12} {'─' * 12} {'─' * 10} {'─' * 6} {'─' * 8}")

    for idx, ug in enumerate(usinas):
        nome = ug["name"]
        status = ug["status"]
        icone = _cor_status(status)
        power = ug["power_kw"]
        pot_max = ug["pot_max_kw"]
        percent = ug["percent"]
        tempo_req = tempos_individuais[idx] if idx < len(tempos_individuais) else 0.0

        linhas.append(
            f"  {nome:<20} {icone} {status:<9} {power:>9.1f} kW {pot_max:>7.0f} kW {percent:>5}% {tempo_req:>6.3f}s"
        )

    # Nivel montante
    nivel = resumo_rt.get("nivel_montante")
    nivel_str = f"{nivel:.2f}m" if nivel is not None else "N/A"
    tempo_nivel = tempos_individuais[-1] if tempos_individuais else 0.0
    linhas.append(f"  {'─' * 20} {'─' * 12} {'─' * 12} {'─' * 10} {'─' * 6} {'─' * 8}")
    linhas.append(f"  {'Nivel Montante':<20} {'':12} {nivel_str:>12} {'':>10} {'':>6} {tempo_nivel:>6.3f}s")

    # Resumo
    linhas.append(f"{'─' * 70}")
    total_kw = resumo_rt["total_power_kw"]
    max_kw = resumo_rt["pot_max_total_kw"]
    pct = resumo_rt["percent_total"]
    linhas.append(f"  Total: {total_kw:.1f} kW / {max_kw:.1f} kW  {_barra(pct)} {pct}%")
    linhas.append(f"{'═' * 70}")

    return "\n".join(linhas)


# ── funcao de leitura com medicao de tempo individual ──────────────

def _ler_gauges_com_tempos(codigo_usina):
    """Wrapper que mede o tempo de cada leitura individual."""
    from libs.views.servicos.connect import (
        _carregar_config,
        _ler_dados_ug,
        _ler_nivel_montante,
        api_manager,
    )
    from libs.models.gauge_rt import (
        montar_registros_gauge,
        resolver_status_ug,
        obter_registro_nivel_montante,
    )

    config = _carregar_config()
    chave = codigo_usina.replace("-", " ")
    usina_cfg = config.get(chave)
    if not usina_cfg:
        return [], {"nivel_montante": None, "total_power_kw": 0.0, "percent_total": 0, "pot_max_total_kw": 0.0}, []

    api_ip = usina_cfg["ip"]
    api_port = usina_cfg["port"]
    dispositivos = usina_cfg.get("dispositivos", {})

    UG_COLORS = ["#5BC0EB", "#9B5DE5", "#F15BB5", "#FEE440", "#00F5D4"]

    ugs_para_ler = []
    for nome_disp, disp_cfg in dispositivos.items():
        registros_gauge = montar_registros_gauge(disp_cfg)
        if registros_gauge is None:
            continue
        pot_max_kw = disp_cfg.get("caracteristicas", {}).get("potência máxima", 1)
        conexao = disp_cfg.get("conexao", {})
        ugs_para_ler.append({
            "nome": nome_disp,
            "conexao": conexao,
            "registros": registros_gauge,
            "pot_max_kw": pot_max_kw,
        })

    if not ugs_para_ler:
        return [], {"nivel_montante": None, "total_power_kw": 0.0, "percent_total": 0, "pot_max_total_kw": 0.0}, []

    # Ler UGs medindo tempo individual
    tempos_individuais = []
    resultados = {}
    for ug in ugs_para_ler:
        t0 = time.perf_counter()
        resultado = _ler_dados_ug(api_ip, api_port, codigo_usina, ug["conexao"], ug["registros"], ug["nome"])
        tempos_individuais.append(time.perf_counter() - t0)
        resultados[ug["nome"]] = resultado

    # Ler nivel montante
    t0 = time.perf_counter()
    from libs.models.gauge_rt import NIVEL_MONTANTE_LABEL
    nivel_montante = _ler_nivel_montante(api_ip, api_port, codigo_usina, usina_cfg)
    tempos_individuais.append(time.perf_counter() - t0)

    # Montar gauges
    usinas = []
    for idx, ug in enumerate(ugs_para_ler):
        leituras_rt = resultados.get(ug["nome"])
        pot_max = ug["pot_max_kw"]

        if leituras_rt is not None:
            valor = leituras_rt.get("Potência Ativa")
            status = resolver_status_ug(leituras_rt, codigo_usina=codigo_usina)
        else:
            valor = None
            status = "Offline"

        try:
            power_kw = abs(float(valor)) if valor is not None else 0.0
        except (TypeError, ValueError):
            power_kw = 0.0

        percent = min(round(power_kw / pot_max * 100), 100) if pot_max > 0 else 0

        usinas.append({
            "name": ug["nome"],
            "status": status,
            "percent": percent,
            "power_kw": round(power_kw, 1),
            "pot_max_kw": pot_max,
            "color": UG_COLORS[idx % len(UG_COLORS)],
        })

    total_power_kw = round(sum(u["power_kw"] for u in usinas), 1)
    pot_max_total_kw = round(sum(u["pot_max_kw"] for u in usinas), 1)
    percent_total = min(round(total_power_kw / pot_max_total_kw * 100), 100) if pot_max_total_kw > 0 else 0

    resumo_rt = {
        "nivel_montante": round(float(nivel_montante), 2) if nivel_montante is not None else None,
        "total_power_kw": total_power_kw,
        "percent_total": percent_total,
        "pot_max_total_kw": pot_max_total_kw,
    }

    return usinas, resumo_rt, tempos_individuais


# ── testes pytest ──────────────────────────────────────────────────

def test_ciclo_completo_pch_pira():
    """Ciclo completo PCH-PIRA: todas as UGs + nivel em < 20s."""
    codigo = "PCH-PIRA"

    inicio = time.perf_counter()
    usinas, resumo_rt, tempos = _ler_gauges_com_tempos(codigo)
    tempo_total = time.perf_counter() - inicio

    print(_formatar_resultado_ciclo(codigo, usinas, resumo_rt, tempo_total, tempos))

    assert tempo_total < LIMITE_CICLO_SEGUNDOS, (
        f"Ciclo levou {tempo_total:.1f}s, limite e {LIMITE_CICLO_SEGUNDOS}s"
    )
    assert len(usinas) > 0, "Nenhuma UG retornada"
    for ug in usinas:
        assert ug["status"] != "Offline", f"{ug['name']} esta Offline"


def test_ciclo_completo_todas_usinas():
    """Ciclo completo de cada usina: resposta e tempo."""
    resultados = []
    todas_ok = True

    for codigo in USINAS_PARA_TESTAR:
        inicio = time.perf_counter()
        usinas, resumo_rt, tempos = _ler_gauges_com_tempos(codigo)
        tempo_total = time.perf_counter() - inicio

        print(_formatar_resultado_ciclo(codigo, usinas, resumo_rt, tempo_total, tempos))

        ok = tempo_total < LIMITE_CICLO_SEGUNDOS and len(usinas) > 0
        resultados.append((codigo, ok, tempo_total, len(usinas)))
        if not ok:
            todas_ok = False

    # Resumo final
    print(f"\n{'═' * 70}")
    print(f"  RESUMO GERAL")
    print(f"{'─' * 70}")
    print(f"  {'Usina':<25} {'Status':>8} {'Tempo':>8} {'UGs':>5}")
    print(f"  {'─' * 25} {'─' * 8} {'─' * 8} {'─' * 5}")
    for codigo, ok, tempo, n_ugs in resultados:
        marca = "✅" if ok else "❌"
        print(f"  {codigo:<25} {marca:>8} {tempo:>6.2f}s {n_ugs:>5}")
    print(f"{'═' * 70}")

    assert todas_ok, "Pelo menos uma usina falhou no ciclo"


def test_leituras_individuais_dentro_do_limite():
    """Cada leitura individual deve responder em < 5s."""
    codigo = "PCH-PIRA"
    _, _, tempos = _ler_gauges_com_tempos(codigo)

    for idx, t in enumerate(tempos):
        assert t < LIMITE_LEITURA_INDIVIDUAL, (
            f"Leitura {idx} levou {t:.2f}s, limite e {LIMITE_LEITURA_INDIVIDUAL}s"
        )


def test_api_historica_producao():
    """Verifica se a API de producao historica responde."""
    from libs.models.consultas import consultar_producao, normalizar_energia

    inicio = time.perf_counter()
    resposta = consultar_producao(periodo="D", codigo_usina="PCH-PIRA")
    tempo = time.perf_counter() - inicio

    print(f"\n  API /producao-acumulada: {tempo:.2f}s")

    assert isinstance(resposta, dict), "Resposta nao e dict"
    dados = resposta.get("resultado") or resposta.get("dados")
    assert dados is not None, "Sem campo 'resultado' ou 'dados'"
    assert len(dados) > 0, "Lista de dados vazia"

    df = normalizar_energia(resposta, periodo="D")
    print(f"  DataFrame: {df.shape[0]} linhas x {df.shape[1]} colunas")
    assert not df.empty, "DataFrame vazio apos normalizacao"


def test_api_historica_nivel():
    """Verifica se a API de nivel historico responde."""
    from libs.models.consultas import consultar_nivel, normalizar_nivel

    inicio = time.perf_counter()
    resposta = consultar_nivel(codigo_usina="PCH-PIRA")
    tempo = time.perf_counter() - inicio

    print(f"\n  API /grupo-usina (nivel): {tempo:.2f}s")

    assert isinstance(resposta, dict), "Resposta nao e dict"
    dados = resposta.get("dados") or resposta.get("resultado")
    assert dados is not None, "Sem campo 'dados' ou 'resultado'"
    assert len(dados) > 0, "Lista de dados vazia"

    df = normalizar_nivel(resposta)
    print(f"  DataFrame: {df.shape[0]} linhas x {df.shape[1]} colunas")
    assert not df.empty, "DataFrame vazio apos normalizacao"


# ── execucao direta ────────────────────────────────────────────────

if __name__ == "__main__":
    testes = [
        ("Ciclo RT PCH-PIRA", test_ciclo_completo_pch_pira),
        ("Ciclo RT todas usinas", test_ciclo_completo_todas_usinas),
        ("Leituras individuais < 5s", test_leituras_individuais_dentro_do_limite),
        ("API historica producao", test_api_historica_producao),
        ("API historica nivel", test_api_historica_nivel),
    ]

    print(f"\n{'═' * 70}")
    print(f"  TESTES DE INTEGRACAO — APIs em Tempo Real e Historicas")
    print(f"{'═' * 70}")

    resultados = []
    for nome, fn in testes:
        try:
            fn()
            resultados.append((nome, True, None))
        except Exception as e:
            resultados.append((nome, False, str(e)))

    print(f"\n{'═' * 70}")
    print(f"  RESULTADO FINAL")
    print(f"{'─' * 70}")
    for nome, ok, erro in resultados:
        marca = "✅ PASS" if ok else "❌ FAIL"
        print(f"  {marca}  {nome}")
        if erro:
            print(f"         {erro}")
    print(f"{'═' * 70}")

    total = len(resultados)
    ok_count = sum(1 for _, ok, _ in resultados if ok)
    print(f"  {ok_count}/{total} testes passaram")
    print()

    sys.exit(0 if ok_count == total else 1)
