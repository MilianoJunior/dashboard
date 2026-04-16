# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. dispositivo_tem_gauge  -> Valida se o dispositivo tem leituras minimas
# 2. montar_registros_gauge -> Seleciona os registradores usados no gauge RT
# 3. obter_leitura_nivel_montante -> Localiza a leitura de nivel montante
# 4. resolver_status_ug     -> Resolve status por coerencia entre booleanos e potencia
# -------------------------------------------------------------------

STATUS_LABEL_ORDER = [
    "US (sincronizado)",
    "UMD (marcha desexcitada)",
    "UPS (pronta para sincronização)",
    "UPGM (pronta para giro mecânico)",
    "UP (parada)",
]

STATUS_DISPLAY_BY_LABEL = {
    "US (sincronizado)": "US",
    "UMD (marcha desexcitada)": "UMD",
    "UPS (pronta para sincronização)": "UPS",
    "UPGM (pronta para giro mecânico)": "UPGM",
    "UP (parada)": "UP",
}

STATUS_SEM_GERACAO = {
    "UMD (marcha desexcitada)",
    "UPS (pronta para sincronização)",
    "UPGM (pronta para giro mecânico)",
    "UP (parada)",
}

GAUGE_BASE_LABELS = ("Potência Ativa",)
NIVEL_MONTANTE_LABEL = "Nível Montante"


def _potencia_ativa_kw(leituras_rt):
    valor = leituras_rt.get("Potência Ativa", 0)
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def montar_registros_gauge(dispositivo_cfg):
    leituras = dispositivo_cfg.get("leituras", {})
    registros = {}

    for label in (*GAUGE_BASE_LABELS, *STATUS_LABEL_ORDER):
        registro = leituras.get(label)
        if registro is None:
            return None
        registros[label] = registro

    return registros


def dispositivo_tem_gauge(dispositivo_cfg):
    return montar_registros_gauge(dispositivo_cfg) is not None


def obter_registro_nivel_montante(usina_cfg):
    dispositivos = usina_cfg.get("dispositivos", {})

    for nome_disp, disp_cfg in dispositivos.items():
        leituras = disp_cfg.get("leituras", {})
        registro = leituras.get(NIVEL_MONTANTE_LABEL)
        if registro is not None:
            return {
                "nome": nome_disp,
                "conexao": disp_cfg.get("conexao", {}),
                "registro": registro,
            }

    return None

def _estados_booleanos(leituras_rt):
    return {
        label: leituras_rt.get(label)
        for label in STATUS_LABEL_ORDER
        if isinstance(leituras_rt.get(label), bool)
    }


def _status_display(label):
    return STATUS_DISPLAY_BY_LABEL.get(label, "SEM STATUS")


def _estado_divergente_coerente(label, potencia_kw):
    if potencia_kw > 0:
        return label == "US (sincronizado)"
    return label in STATUS_SEM_GERACAO


def resolver_status_ug(leituras_rt, codigo_usina=None):
    estados = _estados_booleanos(leituras_rt)
    potencia_kw = _potencia_ativa_kw(leituras_rt)

    estados_true = [label for label, ativo in estados.items() if ativo is True]
    estados_false = [label for label, ativo in estados.items() if ativo is False]

    if len(estados_true) == 1:
        return _status_display(estados_true[0])

    if potencia_kw > 0:
        return _status_display("US (sincronizado)")

    if len(estados_false) == 1:
        estado_divergente = estados_false[0]
        if _estado_divergente_coerente(estado_divergente, potencia_kw):
            return _status_display(estado_divergente)

    if potencia_kw <= 0:
        return _status_display("UP (parada)")

    return "SEM STATUS"
