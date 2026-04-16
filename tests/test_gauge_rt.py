# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. test_dispositivo_tem_gauge_exige_status -> Garante labels minimas do card
# 2. test_montar_registros_gauge             -> Mantem ordem esperada da leitura
# 3. test_obter_registro_nivel_montante      -> Localiza a leitura agregada
# 4. test_resolver_status_true_unico         -> Usa o unico True booleano
# 5. test_resolver_status_potencia_forca_us  -> Potencia positiva privilegia US
# 6. test_resolver_status_false_coerente     -> Usa False unico coerente sem geracao
# 7. test_resolver_status_ambiguo_sem_geracao-> Ambiguidade sem potencia privilegia UP
# 8. test_resolver_status_logs_reais         -> Reproduz leituras observadas em log
# -------------------------------------------------------------------

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from libs.models.gauge_rt import (
    STATUS_LABEL_ORDER,
    dispositivo_tem_gauge,
    montar_registros_gauge,
    obter_registro_nivel_montante,
    resolver_status_ug,
)


def _mock_dispositivo():
    leituras = {"Potência Ativa": [13407, "INT", {"offset": -1}]}
    for indice, label in enumerate(STATUS_LABEL_ORDER, start=1):
        leituras[label] = [20000 + indice, "BOOLEAN", {"offset": -1}]
    return {"leituras": leituras}


def test_dispositivo_tem_gauge_exige_status():
    dispositivo = _mock_dispositivo()
    assert dispositivo_tem_gauge(dispositivo) is True

    dispositivo["leituras"].pop("UPS (pronta para sincronização)")
    assert dispositivo_tem_gauge(dispositivo) is False


def test_montar_registros_gauge():
    registros = montar_registros_gauge(_mock_dispositivo())
    assert list(registros.keys()) == ["Potência Ativa", *STATUS_LABEL_ORDER]


def test_obter_registro_nivel_montante():
    usina_cfg = {
        "dispositivos": {
            "PSA": {
                "conexao": {"ip": "10.0.0.1", "port": 502},
                "leituras": {"Nível Montante": [100, "REAL", {"offset": 0}]},
            },
            "UG-01": _mock_dispositivo(),
        }
    }

    leitura = obter_registro_nivel_montante(usina_cfg)

    assert leitura == {
        "nome": "PSA",
        "conexao": {"ip": "10.0.0.1", "port": 502},
        "registro": [100, "REAL", {"offset": 0}],
    }


def test_resolver_status_true_unico():
    leituras_rt = {
        "Potência Ativa": 0.0,
        "US (sincronizado)": False,
        "UMD (marcha desexcitada)": False,
        "UPS (pronta para sincronização)": True,
        "UPGM (pronta para giro mecânico)": False,
        "UP (parada)": False,
    }

    assert resolver_status_ug(leituras_rt, codigo_usina="CGH-FAE") == "UPS"


def test_resolver_status_log_pira_parada():
    leituras_rt = {
        "Potência Ativa": 0.0,
        "US (sincronizado)": False,
        "UMD (marcha desexcitada)": False,
        "UPS (pronta para sincronização)": False,
        "UPGM (pronta para giro mecânico)": False,
        "UP (parada)": True,
    }

    assert resolver_status_ug(leituras_rt, codigo_usina="PCH-PIRA") == "UP"


def test_resolver_status_log_aparecida_gerando():
    leituras_rt = {
        "Potência Ativa": 440,
        "US (sincronizado)": True,
        "UMD (marcha desexcitada)": False,
        "UPS (pronta para sincronização)": False,
        "UPGM (pronta para giro mecânico)": False,
        "UP (parada)": False,
    }

    assert resolver_status_ug(leituras_rt, codigo_usina="CGH-APARECIDA") == "US"


def test_resolver_status_potencia_forca_us_antes_de_false_unico():
    leituras_rt = {
        "Potência Ativa": 440,
        "US (sincronizado)": True,
        "UMD (marcha desexcitada)": True,
        "UPS (pronta para sincronização)": False,
        "UPGM (pronta para giro mecânico)": True,
        "UP (parada)": True,
    }

    assert resolver_status_ug(leituras_rt, codigo_usina="CGH-APARECIDA") == "US"


def test_resolver_status_false_unico_coerente_sem_geracao():
    leituras_rt = {
        "Potência Ativa": 0.0,
        "US (sincronizado)": True,
        "UMD (marcha desexcitada)": True,
        "UPS (pronta para sincronização)": False,
        "UPGM (pronta para giro mecânico)": True,
        "UP (parada)": True,
    }

    assert resolver_status_ug(leituras_rt, codigo_usina="PCH-PIRA") == "UPS"


def test_resolver_status_false_unico_incoerente_sem_geracao_cai_para_up():
    leituras_rt = {
        "Potência Ativa": 0.0,
        "US (sincronizado)": False,
        "UMD (marcha desexcitada)": True,
        "UPS (pronta para sincronização)": True,
        "UPGM (pronta para giro mecânico)": True,
        "UP (parada)": True,
    }

    assert resolver_status_ug(leituras_rt, codigo_usina="PCH-PIRA") == "UP"


def test_resolver_status_ambiguo_sem_geracao_privilegia_up():
    leituras_rt = {
        "Potência Ativa": 0.0,
        "US (sincronizado)": False,
        "UMD (marcha desexcitada)": True,
        "UPS (pronta para sincronização)": True,
        "UPGM (pronta para giro mecânico)": False,
        "UP (parada)": False,
    }

    assert resolver_status_ug(leituras_rt, codigo_usina="PCH-PIRA") == "UP"
