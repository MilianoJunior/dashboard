import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib import error, request as urllib_request

from flask_socketio import SocketIO

socketio = SocketIO(async_mode="threading")

UG_COLORS = ["#5BC0EB", "#9B5DE5", "#F15BB5", "#FEE440", "#00F5D4"]

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "config", "usinas_dispositivos.json"
)
_config_cache = None

# Usina selecionada (compartilhada entre clientes)
_usina_atual = "PCH-PIRA"


def _carregar_config():
    global _config_cache
    if _config_cache is None:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            _config_cache = json.load(f)
    return _config_cache


def _ler_potencia_ug(api_ip, api_port, conexao, registro_potencia, nome_ug):
    """POST na API Modbus para ler Potência Ativa de uma UG.
    Retorna o valor lido ou None em caso de erro.
    """
    url = f"http://{api_ip}:{api_port}/readCLP/leituras"
    body = {
        "conexao": {
            "ip": conexao["ip"],
            "port": conexao["port"],
            "timeout": conexao.get("timeout", 10.0),
        },
        "registers": {
            "Potência Ativa": registro_potencia,
        },
    }
    req = urllib_request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=5) as resp:
            resultado = json.loads(resp.read().decode("utf-8"))
            if resultado.get("status") == "success":
                valor = resultado.get("data", {}).get("Potência Ativa")
                print(
                    f"[SOCKET] {nome_ug} -> Potência Ativa = {valor}",
                    flush=True,
                )
                return valor
            else:
                msg = resultado.get("message", "erro desconhecido")
                print(f"[SOCKET] {nome_ug} -> API erro: {msg}", flush=True)
    except error.URLError as e:
        print(f"[SOCKET] {nome_ug} -> Falha conexão: {e.reason}", flush=True)
    except Exception as e:
        print(f"[SOCKET] {nome_ug} -> Erro: {e}", flush=True)
    return None


def _ler_gauges_usina(codigo_usina):
    """Lê Potência Ativa de cada UG da usina via API Modbus (paralelo)."""
    config = _carregar_config()
    chave = codigo_usina.replace("-", " ")
    usina_cfg = config.get(chave)
    if not usina_cfg:
        print(f"[SOCKET] Usina '{chave}' não encontrada no config", flush=True)
        return []

    api_ip = usina_cfg["ip"]
    api_port = usina_cfg["port"]
    dispositivos = usina_cfg.get("dispositivos", {})

    # Filtrar apenas dispositivos que possuem "Potência Ativa"
    ugs_para_ler = []
    for nome_disp, disp_cfg in dispositivos.items():
        leituras = disp_cfg.get("leituras", {})
        potencia_reg = leituras.get("Potência Ativa")
        if potencia_reg is None:
            continue
        pot_max_kw = disp_cfg.get("caracteristicas", {}).get("potência máxima", 1)
        conexao = disp_cfg.get("conexao", {})
        ugs_para_ler.append({
            "nome": nome_disp,
            "conexao": conexao,
            "registro": potencia_reg,
            "pot_max_kw": pot_max_kw,
        })

    if not ugs_para_ler:
        print(f"[SOCKET] Nenhuma UG com Potência Ativa em '{chave}'", flush=True)
        return []

    # Ler todas as UGs em paralelo (cada leitura pode levar até 5s)
    resultados = {}
    with ThreadPoolExecutor(max_workers=len(ugs_para_ler)) as executor:
        futures = {
            executor.submit(
                _ler_potencia_ug,
                api_ip,
                api_port,
                ug["conexao"],
                ug["registro"],
                ug["nome"],
            ): ug
            for ug in ugs_para_ler
        }
        for future in as_completed(futures):
            ug = futures[future]
            resultados[ug["nome"]] = future.result()

    # Montar lista de gauges na ordem original
    usinas = []
    for idx, ug in enumerate(ugs_para_ler):
        valor = resultados.get(ug["nome"])
        pot_max = ug["pot_max_kw"]

        if valor is not None:
            power_kw = abs(float(valor))
            percent = min(round(power_kw / pot_max * 100), 100) if pot_max > 0 else 0
        else:
            power_kw = 0.0
            percent = 0

        if valor is None:
            status, variant = "Offline", "critical"
        elif percent >= 98:
            status, variant = "Crítico", "critical"
        elif percent >= 90:
            status, variant = "Atenção", "warning"
        else:
            status, variant = "Ativa", "normal"

        usinas.append({
            "name": ug["nome"],
            "status": status,
            "percent": percent,
            "power_kw": round(power_kw, 1),
            "pot_max_kw": pot_max,
            "variant": variant,
            "color": UG_COLORS[idx % len(UG_COLORS)],
        })

    return usinas


def _emitir_gauges():
    """Lê dados reais e envia para todos os clientes."""
    dados = _ler_gauges_usina(_usina_atual)
    socketio.emit("atualizar_gauges", {"usinas": dados, "codigo_usina": _usina_atual})


def iniciar_emissao_periodica(app):
    """Loop que emite dados dos gauges a cada 20 segundos."""
    def _loop():
        while True:
            socketio.sleep(20)
            with app.app_context():
                _emitir_gauges()

    socketio.start_background_task(_loop)


def registrar_eventos():
    """Registra os eventos do SocketIO."""

    @socketio.on("connect")
    def handle_connect():
        print(f"[SOCKET] Cliente conectado — usina: {_usina_atual}", flush=True)
        dados = _ler_gauges_usina(_usina_atual)
        socketio.emit("atualizar_gauges", {"usinas": dados, "codigo_usina": _usina_atual})

    @socketio.on("selecionar_usina")
    def handle_selecionar_usina(data):
        global _usina_atual
        nova = data.get("usina", _usina_atual)
        if nova != _usina_atual:
            _usina_atual = nova
            print(f"[SOCKET] Usina alterada para: {_usina_atual}", flush=True)
        # Emitir imediatamente para a nova usina
        dados = _ler_gauges_usina(_usina_atual)
        socketio.emit("atualizar_gauges", {"usinas": dados, "codigo_usina": _usina_atual})

    @socketio.on("disconnect")
    def handle_disconnect():
        print("[SOCKET] Cliente desconectado", flush=True)
