# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. dispositivo_tem_gauge  -> Valida se o dispositivo tem leituras minimas
# 2. montar_registros_gauge -> Seleciona os registradores usados no gauge RT
# 3. obter_leitura_nivel_montante -> Localiza a leitura de nivel montante
# 4. resolver_status_ug     -> Resolve o status ativo da UG por ordem
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

GAUGE_BASE_LABELS = ("Potência Ativa",)
NIVEL_MONTANTE_LABEL = "Nível Montante"


def _status_ativo(valor):
    if isinstance(valor, bool):
        return valor

    if isinstance(valor, (int, float)):
        return valor != 0

    texto = str(valor).strip().lower()
    return texto in {"1", "1.0", "true", "on", "sim", "yes"}


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

def _status_corresponde_ao_estado(valor, codigo_usina):
    # print(f" 1 [DEBUG] _status_corresponde_ao_estado: valor={valor}, codigo_usina={codigo_usina}")
    ativo = _status_ativo(valor)
    # print(f" 2 [DEBUG] _status_corresponde_ao_estado: valor={valor}, codigo_usina={codigo_usina}")
    # if codigo_usina == "PCH-PIRA":
    #     return not ativo
    return ativo

cont = 0

def resolver_status_ug(leituras_rt, codigo_usina=None):
    global cont
    cont += 1
    # print(" ")
    # print(f" 3 [DEBUG] resolver_status_ug: cont={cont}, codigo_usina={codigo_usina}")
    for label in STATUS_LABEL_ORDER:
        if _status_corresponde_ao_estado(leituras_rt.get(label), codigo_usina):
            return STATUS_DISPLAY_BY_LABEL[label]

    return "SEM STATUS"
