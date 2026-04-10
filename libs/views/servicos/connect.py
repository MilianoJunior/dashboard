# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. _carregar_config   -> Carrega o JSON de dispositivos
# 2. _ler_dados_ug      -> Lê potência e status da UG via API Modbus usando ConexaoAPI
# 3. _ler_nivel_montante-> Lê nível montante via API Modbus usando ConexaoAPI
# 4. _ler_gauges_usina  -> Monta os gauges RT de uma usina em paralelo
# 5. ConexaoSocketIO    -> Instância que gerencia usina_atual e emissão dos dados
# 6. Event handlers     -> Funções globais que interagem com ConexaoSocketIO
# -------------------------------------------------------------------

import hashlib
import inspect
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib import error, request as urllib_request

from flask_socketio import SocketIO

from libs.models.gauge_rt import (
    NIVEL_MONTANTE_LABEL,
    montar_registros_gauge,
    obter_registro_nivel_montante,
    resolver_status_ug,
)

socketio = SocketIO(async_mode="threading")

UG_COLORS = ["#5BC0EB", "#9B5DE5", "#F15BB5", "#FEE440", "#00F5D4"]

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "config", "usinas_dispositivos.json"
)
_config_cache = None


class ConexaoAPI:
    """Responsável exclusivo pelas transações HTTP com a API Modbus"""
    
    _observabilidade_historico = []
    _MAX_HISTORICO = 200
    _JANELA_SEGUNDOS = 15
    
    def __init__(self):
        self.contador = 0
        self.erro = 0

    def read_clp(self, ip, port, body, tipo="leituras", timeout=5, log_context="API"):
        self.contador += 1
        url = f"http://{ip}:{port}/readCLP/{tipo}"
        req = urllib_request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # registros = json.dumps(body.get('registers', {}), indent=4, ensure_ascii=False)
        registros = body.get('registers', {}).keys()
        start = time.time()
        print(' ')
        print(f" {self.contador} [DEBUG] read_clp: body={body.get('conexao', {}).get('ip', ip)}:{body.get('conexao', {}).get('port', port)}")
        print(list(registros))
        try:
            with urllib_request.urlopen(req, timeout=timeout) as resp:
                resultado = json.loads(resp.read().decode("utf-8"))
                if resultado.get("status") == "success":
                    resp = resultado.get("data", {})
                    end = time.time()
                    print(f"resp={resp} | Tempo: {round(end - start, 3)}")
                    return resp
                else:
                    msg = resultado.get("message", "erro desconhecido")
                    print(f"[SOCKET] {log_context} -> API erro: {msg}", flush=True)
        except error.URLError as e:
            print(f"[SOCKET] {log_context} -> Falha conexão: {e.reason}", flush=True)
            self.erro += 1
        except Exception as e:
            print(f"[SOCKET] {log_context} -> Erro: {e}", flush=True)
            self.erro += 1
        # finally:
        #     self.diagnostic_connections(ip, port, timeout, log_context)
        #     self.close_connections(ip, port, timeout, log_context)
        if self.erro > 0:
            print('###############')  
            print(f'Quantidades de erros: {self.erro}')
            print('###############')
            
        return None
            
    def close_connections(self, ip, port, timeout=5, log_context="API"):
        url = f"http://{ip}:{port}/closeConnections"
        req = urllib_request.Request(
            url,
            method="POST",
        )
        try:
            with urllib_request.urlopen(req, timeout=timeout) as resp:
                resultado = json.loads(resp.read().decode("utf-8"))
                if resultado.get("status") == "success":
                    print(f" [DEBUG] close_connections: resp={resultado}")
                else:
                    msg = resultado.get("message", "erro desconhecido")
                    print(f"[SOCKET] {log_context} -> API erro close: {msg}", flush=True)
        except error.URLError as e:
            print(f"[SOCKET] {log_context} -> Falha close: {e.reason}", flush=True)
        except Exception as e:
            print(f"[SOCKET] {log_context} -> Erro close: {e}", flush=True)
            
        return False

    def diagnostic_connections(self, ip, port, timeout=5, log_context="API"):
        url = f"http://{ip}:{port}/diagnostics"
        req = urllib_request.Request(
            url,
            method="GET",
        )
        try:
            with urllib_request.urlopen(req, timeout=timeout) as resp:
                resultado = json.loads(resp.read().decode("utf-8"))
                if resultado.get("status") == "success":
                    print(f" [DEBUG] diagnostic_connections: resp={resultado}")
                else:
                    msg = resultado.get("message", "erro desconhecido")
                    print(f"[SOCKET] {log_context} -> API erro close: {msg}", flush=True)
        except error.URLError as e:
            print(f"[SOCKET] {log_context} -> Falha close: {e.reason}", flush=True)
        except Exception as e:
            print(f"[SOCKET] {log_context} -> Erro close: {e}", flush=True)
            
        return False


# Singleton global de gerência HTTP
api_manager = ConexaoAPI()


def _carregar_config():
    global _config_cache
    if _config_cache is None:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            _config_cache = json.load(f)
    return _config_cache


def _ler_dados_ug(api_ip, api_port, codigo_usina, conexao, registros_gauge, nome_ug):
    """POST na API Modbus para ler potência e status de uma UG.
    Retorna o payload `data` da API ou None em caso de erro.
    """
    body = {
        "conexao": {
            "ip": conexao["ip"],
            "port": conexao["port"],
            "timeout": conexao.get("timeout", 10.0),
        },
        "registers": registros_gauge,
    }
    
    leituras_rt = api_manager.read_clp(api_ip, api_port, body, tipo="leituras", timeout=5, log_context=nome_ug)
    
    if leituras_rt is not None:
        valor = leituras_rt.get("Potência Ativa")
        status = resolver_status_ug(leituras_rt, codigo_usina=codigo_usina)
        leituras_log = json.dumps(leituras_rt, ensure_ascii=False, sort_keys=True)
        print(
            f"[SOCKET] {codigo_usina} | {nome_ug} -> Leituras RT = {leituras_log} | "
            f"Potência Ativa = {valor} | Status = {status}",
            flush=True,
        )
        return leituras_rt

    return None


def _ler_nivel_montante(api_ip, api_port, codigo_usina, usina_cfg):
    leitura_nivel = obter_registro_nivel_montante(usina_cfg)
    if leitura_nivel is None:
        print(f"[SOCKET] {codigo_usina} -> Nível Montante não configurado", flush=True)
        return None

    body = {
        "conexao": {
            "ip": leitura_nivel["conexao"]["ip"],
            "port": leitura_nivel["conexao"]["port"],
            "timeout": leitura_nivel["conexao"].get("timeout", 10.0),
        },
        "registers": {
            NIVEL_MONTANTE_LABEL: leitura_nivel["registro"],
        },
    }
    
    data = api_manager.read_clp(api_ip, api_port, body, tipo="leituras", timeout=5, log_context=codigo_usina)
    
    if data is not None:
        nivel = data.get(NIVEL_MONTANTE_LABEL)
        print(
            f"[SOCKET] {codigo_usina} | {leitura_nivel['nome']} -> "
            f"Nível Montante = {nivel}",
            flush=True,
        )
        return nivel

    return None


def _ler_gauges_usina(codigo_usina):
    """Lê potência e status de cada UG elegível da usina via API Modbus."""
    config = _carregar_config()
    chave = codigo_usina.replace("-", " ")
    usina_cfg = config.get(chave)
    if not usina_cfg:
        print(f"[SOCKET] Usina '{chave}' não encontrada no config", flush=True)
        return [], {
            "nivel_montante": None,
            "total_power_kw": 0.0,
            "percent_total": 0,
            "pot_max_total_kw": 0.0,
        }

    api_ip = usina_cfg["ip"]
    api_port = usina_cfg["port"]
    dispositivos = usina_cfg.get("dispositivos", {})

    # Filtrar apenas dispositivos que possuem potência e todas as labels de status.
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
        print(f"[SOCKET] Nenhuma UG elegível para gauge em '{chave}'", flush=True)
        return [], {
            "nivel_montante": None,
            "total_power_kw": 0.0,
            "percent_total": 0,
            "pot_max_total_kw": 0.0,
        }

    # Ler todas as UGs de forma sequencial para evitar timeouts e sobrecarga na API
    resultados = {}
    for ug in ugs_para_ler:
        resultado = _ler_dados_ug(
            api_ip,
            api_port,
            codigo_usina,
            ug["conexao"],
            ug["registros"],
            ug["nome"],
        )
        resultados[ug["nome"]] = resultado

    
    # api_manager.diagnostic_connections(api_ip, api_port)
    # api_manager.close_connections(api_ip, api_port)

    # Montar lista de gauges na ordem original
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

    total_power_kw = round(sum(ug["power_kw"] for ug in usinas), 1)
    pot_max_total_kw = round(sum(ug["pot_max_kw"] for ug in usinas), 1)
    percent_total = (
        min(round(total_power_kw / pot_max_total_kw * 100), 100)
        if pot_max_total_kw > 0
        else 0
    )
    nivel_montante = _ler_nivel_montante(
        api_ip=api_ip,
        api_port=api_port,
        codigo_usina=codigo_usina,
        usina_cfg=usina_cfg,
    )

    resumo_rt = {
        "nivel_montante": round(float(nivel_montante), 2) if nivel_montante is not None else None,
        "total_power_kw": total_power_kw,
        "percent_total": percent_total,
        "pot_max_total_kw": pot_max_total_kw,
    }

    return usinas, resumo_rt


class ConexaoSocketIO:
    """Responsável por gerenciar o estado e eventos do WebSocket."""
    
    def __init__(self, sio):
        self.sio = sio
        self.usina_atual = "PCH-PIRA"
        self.contador = 0
        self.tempo = time.time()
        self.clientes_conectados = 0

    def emitir_gauges(self):
        """Lê dados reais e envia para todos os clientes."""
        if self.clientes_conectados == 0:
            return
        self.contador += 1
        tempo_atual = time.time()
        print(' ')
        print('-------------------------------------------------------------')
        print(f" Ciclo: {self.contador} Tempo: {tempo_atual - self.tempo}")
        if tempo_atual - self.tempo > 15:
            self.tempo = tempo_atual
            usinas, resumo_rt = _ler_gauges_usina(self.usina_atual)
            self.sio.emit(
                "atualizar_gauges",
                {
                "usinas": usinas,
                "resumo_rt": resumo_rt,
                "codigo_usina": self.usina_atual,
            },
        )

    def iniciar_emissao_periodica(self, app):
        """Loop que emite dados dos gauges a cada 20 segundos."""
        def _loop():
            while True:
                self.sio.sleep(20)
                with app.app_context():
                    self.emitir_gauges()

        self.sio.start_background_task(_loop)

    def registrar_eventos(self):
        """Registra os eventos do SocketIO."""
        @self.sio.on("connect")
        def handle_connect():
            self.clientes_conectados += 1
            print(f"[SOCKET] Cliente conectado (total: {self.clientes_conectados})", flush=True)
            self.emitir_gauges()

        @self.sio.on("selecionar_usina")
        def handle_selecionar_usina(data):
            nova = data.get("usina", self.usina_atual)
            if nova != self.usina_atual:
                self.usina_atual = nova
            self.emitir_gauges()

        @self.sio.on("page_loaded")
        def handle_page_loaded(data):
            shell = data.get("shell_ms", 0)
            dados = data.get("data_ms", 0)
            total = shell + dados if dados else shell
            print(
                f"[PERF] Página carregada em {total}ms "
                f"(Shell: {shell}ms | Dados: {dados}ms)",
                flush=True,
            )

        @self.sio.on("disconnect")
        def handle_disconnect():
            self.clientes_conectados = max(0, self.clientes_conectados - 1)
            print(f"[SOCKET] Cliente desconectado (total: {self.clientes_conectados})", flush=True)


# ===================================================================
# INSTÂNCIA PÚBLICA E FUNÇÕES GLOBAIS (Não quebra o entrypoint atual do app)
# ===================================================================
socket_manager = ConexaoSocketIO(socketio)


def iniciar_emissao_periodica(app):
    socket_manager.iniciar_emissao_periodica(app)


def registrar_eventos():
    socket_manager.registrar_eventos()


'''
data: {
    'server_timestamp': 1775666590.6077511, 
    'active_connections_count': 5, 
    'connections': [
        {'connection': '10.200.20.11:502', 'connected': True, 'last_used': 1775666582.1603782, 'idle_time_seconds': 8.43}, 
        {'connection': '10.200.20.21:502', 'connected': True, 'last_used': 1775666582.1592762, 'idle_time_seconds': 8.43}, 
        {'connection': '10.200.20.31:502', 'connected': True, 'last_used': 1775666582.1598194, 'idle_time_seconds': 8.43}, 
        {'connection': '10.200.20.41:502', 'connected': True, 'last_used': 1775666582.160115, 'idle_time_seconds': 8.43}, 
        {'connection': '10.200.20.51:502', 'connected': True, 'last_used': 1775666582.1605704, 'idle_time_seconds': 8.43}], 
    'logs': [
        '2026-04-08 13:41:58,627 [INFO] 08/04/2026 13:41:58 [PERFORMANCE] Tempo: 0.446s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:41:58,628 [INFO] 08/04/2026 13:41:58 [PERFORMANCE] Tempo: 0.443s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:41:58,631 [INFO] 08/04/2026 13:41:58 [PERFORMANCE] Tempo: 0.448s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:41:58,640 [INFO] 08/04/2026 13:41:58 [PERFORMANCE] Tempo: 0.455s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:41:58,643 [INFO] 08/04/2026 13:41:58 [PERFORMANCE] Tempo: 0.460s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:41:59,346 [INFO] 08/04/2026 13:41:59 [PERFORMANCE] Tempo: 0.462s | Pacotes: 12 | Tags Lidas: 6',
        '2026-04-08 13:41:59,347 [INFO] 08/04/2026 13:41:59 [PERFORMANCE] Tempo: 0.461s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:41:59,351 [INFO] 08/04/2026 13:41:59 [PERFORMANCE] Tempo: 0.465s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:41:59,360 [INFO] 08/04/2026 13:41:59 [PERFORMANCE] Tempo: 0.473s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:41:59,363 [INFO] 08/04/2026 13:41:59 [PERFORMANCE] Tempo: 0.477s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:00,591 [INFO] 08/04/2026 13:42:00 [PERFORMANCE] Tempo: 0.442s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:00,600 [INFO] 08/04/2026 13:42:00 [PERFORMANCE] Tempo: 0.450s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:00,603 [INFO] 08/04/2026 13:42:00 [PERFORMANCE] Tempo: 0.454s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:00,627 [INFO] 08/04/2026 13:42:00 [PERFORMANCE] Tempo: 0.478s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:00,628 [INFO] 08/04/2026 13:42:00 [PERFORMANCE] Tempo: 0.477s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:15,851 [INFO] 08/04/2026 13:42:15 [PERFORMANCE] Tempo: 0.446s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:15,867 [INFO] 08/04/2026 13:42:15 [PERFORMANCE] Tempo: 0.463s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:15,868 [INFO] 08/04/2026 13:42:15 [PERFORMANCE] Tempo: 0.461s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:15,881 [INFO] 08/04/2026 13:42:15 [PERFORMANCE] Tempo: 0.474s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:15,884 [INFO] 08/04/2026 13:42:15 [PERFORMANCE] Tempo: 0.479s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:29,428 [INFO] 08/04/2026 13:42:29 [PERFORMANCE] Tempo: 0.452s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:29,428 [INFO] 08/04/2026 13:42:29 [PERFORMANCE] Tempo: 0.451s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:29,441 [INFO] 08/04/2026 13:42:29 [PERFORMANCE] Tempo: 0.463s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:29,445 [INFO] 08/04/2026 13:42:29 [PERFORMANCE] Tempo: 0.468s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:29,451 [INFO] 08/04/2026 13:42:29 [PERFORMANCE] Tempo: 0.475s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:31,921 [INFO] 08/04/2026 13:42:31 [PERFORMANCE] Tempo: 0.444s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:31,925 [INFO] 08/04/2026 13:42:31 [PERFORMANCE] Tempo: 0.448s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:31,931 [INFO] 08/04/2026 13:42:31 [PERFORMANCE] Tempo: 0.454s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:31,947 [INFO] 08/04/2026 13:42:31 [PERFORMANCE] Tempo: 0.470s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:31,948 [INFO] 08/04/2026 13:42:31 [PERFORMANCE] Tempo: 0.471s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:45,828 [INFO] 08/04/2026 13:42:45 [PERFORMANCE] Tempo: 0.441s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:45,842 [INFO] 08/04/2026 13:42:45 [PERFORMANCE] Tempo: 0.454s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:45,845 [INFO] 08/04/2026 13:42:45 [PERFORMANCE] Tempo: 0.458s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:45,851 [INFO] 08/04/2026 13:42:45 [PERFORMANCE] Tempo: 0.465s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:45,868 [INFO] 08/04/2026 13:42:45 [PERFORMANCE] Tempo: 0.481s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:59,332 [INFO] 08/04/2026 13:42:59 [PERFORMANCE] Tempo: 0.447s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:59,349 [INFO] 08/04/2026 13:42:59 [PERFORMANCE] Tempo: 0.464s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:59,349 [INFO] 08/04/2026 13:42:59 [PERFORMANCE] Tempo: 0.462s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:59,362 [INFO] 08/04/2026 13:42:59 [PERFORMANCE] Tempo: 0.475s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:42:59,365 [INFO] 08/04/2026 13:42:59 [PERFORMANCE] Tempo: 0.479s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:43:00,206 [INFO] 08/04/2026 13:43:00 [PERFORMANCE] Tempo: 0.444s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:43:00,211 [INFO] 08/04/2026 13:43:00 [PERFORMANCE] Tempo: 0.450s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:43:00,228 [INFO] 08/04/2026 13:43:00 [PERFORMANCE] Tempo: 0.466s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:43:00,229 [INFO] 08/04/2026 13:43:00 [PERFORMANCE] Tempo: 0.468s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:43:00,242 [INFO] 08/04/2026 13:43:00 [PERFORMANCE] Tempo: 0.480s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:43:02,602 [INFO] 08/04/2026 13:43:02 [PERFORMANCE] Tempo: 0.442s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:43:02,606 [INFO] 08/04/2026 13:43:02 [PERFORMANCE] Tempo: 0.446s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:43:02,611 [INFO] 08/04/2026 13:43:02 [PERFORMANCE] Tempo: 0.453s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:43:02,628 [INFO] 08/04/2026 13:43:02 [PERFORMANCE] Tempo: 0.469s | Pacotes: 12 | Tags Lidas: 6', 
        '2026-04-08 13:43:02,629 [INFO] 08/04/2026 13:43:02 [PERFORMANCE] Tempo: 0.469s | Pacotes: 12 | Tags Lidas: 6']
    }, 
    'status': 'success', 
    'message': 'Diagnóstico realizado com sucesso'
}


'''