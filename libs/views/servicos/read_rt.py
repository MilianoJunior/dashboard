import httpx
import time
from libs.utils.decorators import desempenho

contador = 0
LEITURA_ATIVA = {}
contador_leituras = 0

async def list_modbus_connections(config):
    """Lista todas as conexões Modbus ativas via API."""
    async with httpx.AsyncClient(verify=False, timeout=httpx.Timeout(5.0)) as client:
        try:
            response = await client.get(f"http://{config['ip']}:{config['port']}/listConnections")
            connections_data = response.json()
            if connections_data.get('status') != 'success':
                await close_modbus_connections(config)
                raise Exception(f"[ERRO API] {connections_data.get('message')}")
            return connections_data.get('data'), time.time()
        except Exception as e:
            await close_modbus_connections(config)
            raise Exception(f"[ERRO] {e}")

async def close_modbus_connections(config):
    """Fecha todas as conexões Modbus ativas via API."""
    async with httpx.AsyncClient(verify=False, timeout=httpx.Timeout(5.0)) as client:
        try:
            response = await client.post(f"http://{config['ip']}:{config['port']}/closeConnections")
            connections_data = response.json()
            if connections_data.get('status') != 'success':
                raise Exception(f"[ERRO API] {connections_data.get('message')}")
            return True
        except Exception as e:
            raise Exception(f"[ERRO] {e}")

async def get_data(config, data, nome_usina=None, nome_dispositivo=None):
    global contador_leituras  # Declarar como global antes de usar

    inicio = time.time()
    tipo = config['tipo'] if config['tipo'] != 'temperaturas' else 'leituras'

    registers = data.get('registers')
    contador_leituras += 1
    body = {
        "conexao": data['conexao'],
        "registers": registers
    }

    ip_clp = data['conexao']['ip']
    port_clp = data['conexao']['port']

    # Monta contexto para mensagens de erro
    contexto = ""
    if nome_usina:
        contexto = f"[{nome_usina}"
        if nome_dispositivo:
            contexto += f" - {nome_dispositivo}"
        contexto += "] "

    # Definindo timeout de 3 segundos para a requisição
    contador += 1
    print(f" 3 [DEBUG] get_data: contador={contador}, nome_usina={nome_usina}, nome_dispositivo={nome_dispositivo}")
    timeout = httpx.Timeout(3.0)
    async with httpx.AsyncClient(verify=False, timeout=timeout) as client:
        try:
            response = await client.post(f"http://{config['ip']}:{config['port']}/readCLP/{tipo}", json=body)

            leituras_data = response.json()
            fim = time.time() - inicio
            if leituras_data['status'] == 'success':
                resultado_api = leituras_data['data']
                return resultado_api, fim, None
            else:
                return None, fim, Exception(f"[ERRO] {contexto}{leituras_data.get('message')}")
        except httpx.TimeoutException as e:
            print(f'Erro:  {contexto}[ERRO] Timeout ao conectar em {ip_clp}:{port_clp}')
            raise Exception(f"[ERRO] {contexto}Timeout ao conectar em {ip_clp}:{port_clp}")
        except httpx.ConnectError as e:
            print(f'Erro:  {contexto}[ERRO] Falha ao conectar em {ip_clp}:{port_clp}')
            raise Exception(f"[ERRO] {contexto}Falha ao conectar em {ip_clp}:{port_clp}")
        except Exception as e:
            erro_str = str(e)
            # Se já tiver contexto, não duplicar
            if not erro_str.startswith(f"[ERRO] {contexto}"):
                print(f'Erro:  {contexto}[ERRO] {erro_str}')
                raise Exception(f"[ERRO] {contexto}{erro_str}")
            else:
                print(f'Erro:  {erro_str}')
                raise
        finally:
            LEITURA_ATIVA[config['ip']] = False
