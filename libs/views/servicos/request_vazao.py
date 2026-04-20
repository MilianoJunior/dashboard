'''
# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. _obter_cookie_env -> Lê o cookie salvo no arquivo .env
# 2. _salvar_cookie_env -> Grava ou atualiza o cookie no arquivo .env
# 3. criar_sessao -> Inicia sessão HTTP com o cookie injetado
# 4. autenticar_acesso -> Faz o login, atualiza sessão e salva o novo cookie no .env
# 5. _requisitar_dados_estacao -> Faz o POST para buscar os dados html da tabela
# 6. _extrair_tabela_mensagens -> Parseia o HTML extraindo os registros como dict
# 7. consultar_estacao -> Fluxo principal: tenta baixar dados e, se expirar, reloga
# -------------------------------------------------------------------
'''
import os
import time
import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any

# -------------------------------------------------------------------
# CONFIGURAÇÕES E CONSTANTES
# -------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ENV_PATH = os.path.join(BASE_DIR, ".env")

BASE_URL = "http://servidor.ambitec.eng.br:8080/sistema"
SEARCH_URL = f"{BASE_URL}/engine.php?class=MyMessageList&method=onSearch"
LOGIN_URL = f"{BASE_URL}/engine.php?class=LoginForm&method=onLogin"

# -------------------------------------------------------------------
# FUNÇÕES
# -------------------------------------------------------------------
class ConsultaErro(Exception):
    pass


def _obter_cookie_env() -> str:
    """Lê o cookie PHPSESSID salvo no arquivo .env."""
    if not os.path.exists(ENV_PATH):
        return ""
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for linha in f:
            if linha.startswith("AMBITEC_COOKIE="):
                return linha.split("=", 1)[1].strip()
    return ""


def _salvar_cookie_env(novo_cookie: str) -> None:
    """Grava ou atualiza o cookie PHPSESSID no arquivo .env."""
    linhas = []
    atualizado = False

    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            linhas = f.readlines()

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        for linha in linhas:
            if linha.startswith("AMBITEC_COOKIE="):
                f.write(f"AMBITEC_COOKIE={novo_cookie}\n")
                atualizado = True
            else:
                f.write(linha)
        if not atualizado:
            # Se não terminou com quebra de linha, insere uma para evitar problemas
            if linhas and not linhas[-1].endswith('\n'):
                f.write('\n')
            f.write(f"AMBITEC_COOKIE={novo_cookie}\n")


def criar_sessao() -> requests.Session:
    """Inicia uma sessão HTTP com cookie do .env."""
    session = requests.Session()
    cookie = _obter_cookie_env()
    if cookie:
        print(f"[AUTH] Usando cookie existente: {cookie[:5]}...{cookie[-5:] if len(cookie)>10 else ''}")
        session.cookies.set(
            "PHPSESSID",
            cookie,
            domain="servidor.ambitec.eng.br"
        )
    else:
        print("[AUTH] Nenhum cookie encontrado. Um novo será solicitado.")
    return session


def autenticar_acesso(session: requests.Session) -> None:
    """Realiza o login, atualiza a sessão e salva o novo cookie no .env."""
    payload = {
        "login": "pchpira",
        "password": "PIRA"
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": f"{BASE_URL}/index.php?class=LoginForm",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    response = session.post(LOGIN_URL, data=payload, headers=headers, timeout=20)
    response.raise_for_status()

    novo_cookie = session.cookies.get("PHPSESSID", domain="servidor.ambitec.eng.br")
    if novo_cookie:
        print(f"[AUTH] Login efetuado. Novo cookie gerado: {novo_cookie[:5]}...{novo_cookie[-5:] if len(novo_cookie)>10 else ''}")
        _salvar_cookie_env(novo_cookie)


def _requisitar_dados_estacao(
    session: requests.Session,
    station_id: str,
    data_date: str,
    send_date: str = "",
    register_date: str = "",
    send_status: str = "",
    timeout: int = 20,
) -> str:
    """Baixa o HTML bruto contendo a tabela de mensagens da usina."""
    payload = {
        "station_id": station_id,
        "send_status": send_status,
        "data_date": data_date,
        "register_date": register_date,
        "send_date": send_date,
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": f"{BASE_URL}/index.php?class=MyMessageList",
        "Origin": "http://servidor.ambitec.eng.br:8080",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    response = session.post(SEARCH_URL, data=payload, headers=headers, timeout=timeout)
    response.raise_for_status()

    html = response.text

    if "LoginForm" in html or "onLogin" in html:
        raise ConsultaErro("Sessão inválida ou expirada")

    if "LISTA DE MENSAGENS" not in html and "ESTAÇÃO" not in html:
        raise ConsultaErro("Resposta não parece conter a listagem esperada")

    return html


def _extrair_tabela_mensagens(html: str) -> List[Dict[str, str]]:
    """Faz o parse do HTML e retorna os registros como dicionários."""
    soup = BeautifulSoup(html, "html.parser")

    tabelas = soup.find_all("table")
    if not tabelas:
        raise ConsultaErro("Nenhuma tabela encontrada no HTML")

    tabela_alvo = None
    for tabela in tabelas:
        texto = tabela.get_text(" ", strip=True).upper()
        if "ESTAÇÃO" in texto and "VAZÃO" in texto and "PROCESSAMENTO" in texto:
            tabela_alvo = tabela
            break

    if tabela_alvo is None:
        raise ConsultaErro("Tabela de mensagens não encontrada")

    linhas = tabela_alvo.find_all("tr")
    if len(linhas) < 2:
        return []

    cabecalho = [th.get_text(" ", strip=True) for th in linhas[0].find_all(["th", "td"])]

    dados = []
    for linha in linhas[1:]:
        colunas = linha.find_all("td")
        if not colunas:
            continue

        valores = [td.get_text(" ", strip=True) for td in colunas]

        if len(valores) != len(cabecalho):
            continue

        registro = dict(zip(cabecalho, valores))
        dados.append(registro)

    return dados


def _formatar_resposta_json(dados_brutos: List[Dict[str, str]], data_date: str, tempo_inicio: float) -> Dict[str, Any]:
    """Converte a lista de mensagens brutas para o formato de dicionário final."""
    if not dados_brutos:
        return {}
        
    estacao = dados_brutos[0].get("ESTAÇÃO", "")
    
    dados_formatados = {}
    for row in dados_brutos:
        data_dados = row.get("DATA DADOS", "")
        if not data_dados:
            continue
            
        nivel_str = row.get("NÍVEL", "0").replace("cm", "")
        try:
            nivel = round(float(nivel_str), 2)
        except ValueError:
            nivel = 0.0
            
        try:
            chuva = float(row.get("CHUVA", 0))
        except ValueError:
            chuva = 0.0
            
        try:
            vazao = float(row.get("VAZÃO", 0))
        except ValueError:
            vazao = 0.0
            
        dados_formatados[data_dados] = {
            "nivel": nivel,
            "chuva": chuva,
            "vazao": vazao,
            "recebido_em": row.get("RECEBIMENTO", "")
        }
        
    latencia = int(time.time() - tempo_inicio)
    
    return {
        "estacao": estacao,
        "referencia": data_date,
        "timezone": "-03:00",
        "especificacao": {
            "nivel": {"unidade": "cm"},
            "chuva": {"unidade": "mm"},
            "vazao": {"unidade": "m3/s"}
        },
        "dados": dados_formatados,
        "status_lote": {
            "processado": True,
            "latencia_max_segundos": latencia
        }
    }


def consultar_estacao(
    station_id: str,
    data_date: str,
    send_date: str = "",
    register_date: str = "",
    send_status: str = "",
) -> Dict[str, Any]:
    """Função principal: orquestra a sessão, lida com re-autenticação e extrai dados."""
    tempo_inicio = time.time()
    session = criar_sessao()
    
    try:
        html = _requisitar_dados_estacao(
            session=session,
            station_id=station_id,
            data_date=data_date,
            send_date=send_date,
            register_date=register_date,
            send_status=send_status,
        )
    except ConsultaErro:
        autenticar_acesso(session)
        html = _requisitar_dados_estacao(
            session=session,
            station_id=station_id,
            data_date=data_date,
            send_date=send_date,
            register_date=register_date,
            send_status=send_status,
        )

    dados_brutos = _extrair_tabela_mensagens(html)
    return _formatar_resposta_json(dados_brutos, data_date, tempo_inicio)


# -------------------------------------------------------------------
# EXECUÇÃO
# -------------------------------------------------------------------
if __name__ == "__main__":
    # Teste isolado, sem necessitar passar cookie manual
    dados = consultar_estacao(
        station_id="200",
        data_date="2026-04-20",
        send_date="2026-04-20",
        register_date="",
        send_status="",
    )

    print(json.dumps(dados, indent=2, ensure_ascii=False))


    '''

    '''