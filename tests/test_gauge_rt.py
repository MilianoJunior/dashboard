# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. test_dispositivo_tem_gauge_exige_status -> Garante labels minimas do card
# 2. test_montar_registros_gauge             -> Mantem ordem esperada da leitura
# 3. test_obter_leitura_nivel_montante       -> Localiza a leitura agregada
# 4. test_resolver_status_ug_padrao          -> Usa status True no fluxo padrao
# 5. test_resolver_status_ug_pch_pira        -> Inverte a logica booleana na PIRA
# -------------------------------------------------------------------

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from libs.models.gauge_rt import (
    STATUS_LABEL_ORDER,
    dispositivo_tem_gauge,
    montar_registros_gauge,
    obter_leitura_nivel_montante,
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


def test_obter_leitura_nivel_montante():
    usina_cfg = {
        "dispositivos": {
            "PSA": {
                "conexao": {"ip": "10.0.0.1", "port": 502},
                "leituras": {"Nível Montante": [100, "REAL", {"offset": 0}]},
            },
            "UG-01": _mock_dispositivo(),
        }
    }

    leitura = obter_leitura_nivel_montante(usina_cfg)

    assert leitura == {
        "nome": "PSA",
        "conexao": {"ip": "10.0.0.1", "port": 502},
        "registro": [100, "REAL", {"offset": 0}],
    }


def test_resolver_status_ug_padrao():
    leituras_rt = {
        "US (sincronizado)": False,
        "UMD (marcha desexcitada)": False,
        "UPS (pronta para sincronização)": True,
        "UPGM (pronta para giro mecânico)": False,
        "UP (parada)": False,
    }

    status, variant = resolver_status_ug(leituras_rt, codigo_usina="CGH-FAE")

    assert status == "UPS"
    assert variant == "warning"


def test_resolver_status_ug_pch_pira():
    leituras_rt = {
        "US (sincronizado)": True,
        "UMD (marcha desexcitada)": True,
        "UPS (pronta para sincronização)": False,
        "UPGM (pronta para giro mecânico)": True,
        "UP (parada)": True,
    }

    status, variant = resolver_status_ug(leituras_rt, codigo_usina="PCH-PIRA")

    assert status == "UPS"
    assert variant == "warning"
