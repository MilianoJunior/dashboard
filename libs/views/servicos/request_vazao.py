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
# 8. criar_tabela_vazao_pira -> Garante a tabela MySQL no banco Railway
# 9. salvar_vazao_pira -> Percorre o dict formatado e persiste as leituras
# 10. consultar_e_salvar_estacao -> Consulta a API e grava o lote no banco
# 11. consultar_e_salvar_ultimos_dias -> Sincroniza uma janela diária
# -------------------------------------------------------------------
'''
import os
import time
import json
import requests
from bs4 import BeautifulSoup
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv

# -------------------------------------------------------------------
# CONFIGURAÇÕES E CONSTANTES
# -------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
WORKSPACE_DIR = os.path.dirname(BASE_DIR)
ENV_PATHS = [
    os.path.join(WORKSPACE_DIR, ".env"),
    os.path.join(BASE_DIR, ".env"),
]
ENV_PATH = next((path for path in ENV_PATHS if os.path.exists(path)), ENV_PATHS[0])
for env_path in ENV_PATHS:
    load_dotenv(env_path, override=False)

BASE_URL = "http://servidor.ambitec.eng.br:8080/sistema"
SEARCH_URL = f"{BASE_URL}/engine.php?class=MyMessageList&method=onSearch"
LOGIN_URL = f"{BASE_URL}/engine.php?class=LoginForm&method=onLogin"

SQL_CRIAR_TABELA_VAZAO_PIRA = """
CREATE TABLE IF NOT EXISTS vazao_pira (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    estacao VARCHAR(120) NOT NULL,
    referencia DATE NOT NULL,
    timezone VARCHAR(10) NOT NULL DEFAULT '-03:00',
    data_hora DATETIME NOT NULL,
    nivel DECIMAL(10, 2) NULL,
    chuva DECIMAL(10, 2) NULL,
    vazao DECIMAL(10, 2) NULL,
    recebido_em DATETIME NULL,
    unidade_nivel VARCHAR(20) NOT NULL DEFAULT 'cm',
    unidade_chuva VARCHAR(20) NOT NULL DEFAULT 'mm',
    unidade_vazao VARCHAR(20) NOT NULL DEFAULT 'm3/s',
    processado TINYINT(1) NOT NULL DEFAULT 1,
    latencia_max_segundos INT UNSIGNED NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_vazao_pira_estacao_data (estacao, data_hora),
    KEY idx_vazao_pira_referencia (referencia),
    KEY idx_vazao_pira_data_hora (data_hora)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

SQL_UPSERT_VAZAO_PIRA = """
INSERT INTO vazao_pira (
    estacao,
    referencia,
    timezone,
    data_hora,
    nivel,
    chuva,
    vazao,
    recebido_em,
    unidade_nivel,
    unidade_chuva,
    unidade_vazao,
    processado,
    latencia_max_segundos
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
ON DUPLICATE KEY UPDATE
    referencia = VALUES(referencia),
    timezone = VALUES(timezone),
    nivel = VALUES(nivel),
    chuva = VALUES(chuva),
    vazao = VALUES(vazao),
    recebido_em = VALUES(recebido_em),
    unidade_nivel = VALUES(unidade_nivel),
    unidade_chuva = VALUES(unidade_chuva),
    unidade_vazao = VALUES(unidade_vazao),
    processado = VALUES(processado),
    latencia_max_segundos = VALUES(latencia_max_segundos);
"""

# -------------------------------------------------------------------
# FUNÇÕES
# -------------------------------------------------------------------
class ConsultaErro(Exception):
    pass


class BancoErro(Exception):
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


def _obter_env(*nomes: str, default: Optional[str] = None) -> Optional[str]:
    """Retorna a primeira variável de ambiente preenchida."""
    for nome in nomes:
        valor = os.getenv(nome)
        if valor:
            return valor
    return default


def _config_banco_railway() -> Dict[str, Any]:
    """Monta a configuração MySQL aceitando variáveis Railway e aliases locais."""
    mysql_url = _obter_env("MYSQL_URL", "DATABASE_URL")
    if mysql_url:
        parsed = urlparse(mysql_url)
        if parsed.scheme.startswith("mysql"):
            return {
                "host": parsed.hostname,
                "port": parsed.port or 3306,
                "user": unquote(parsed.username or ""),
                "password": unquote(parsed.password or ""),
                "database": (parsed.path or "").lstrip("/") or None,
            }

    config = {
        "host": _obter_env("DB_HOST", "MYSQLHOST", "MYSQL_HOST"),
        "port": _obter_env("DB_PORT", "MYSQLPORT", "MYSQL_PORT", default="3306"),
        "user": _obter_env("DB_USER", "MYSQLUSER", "MYSQL_USER"),
        "password": _obter_env("DB_PASSWORD", "MYSQLPASSWORD", "MYSQL_PASSWORD", "MYSQL_PASS"),
        "database": _obter_env("DB_NAME", "MYSQLDATABASE", "MYSQL_DATABASE", "MYSQL_DB"),
    }

    ausentes = [chave for chave, valor in config.items() if not valor and chave != "port"]
    if ausentes:
        nomes = ", ".join(ausentes)
        raise BancoErro(f"Variáveis de banco ausentes: {nomes}")

    try:
        config["port"] = int(config["port"])
    except (TypeError, ValueError) as exc:
        raise BancoErro(f"Porta MySQL inválida: {config['port']}") from exc

    return config


def _abrir_conexao_banco():
    """Abre conexão com o MySQL da Railway."""
    try:
        import mysql.connector
    except ImportError as exc:
        raise BancoErro(
            "Dependência ausente: instale mysql-connector-python para salvar no MySQL"
        ) from exc

    config = _config_banco_railway()
    return mysql.connector.connect(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        database=config["database"],
        connection_timeout=10,
    )


def _normalizar_data_mysql(valor: Any) -> str:
    if isinstance(valor, datetime):
        return valor.date().isoformat()

    texto = str(valor or "").strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date().isoformat()
        except ValueError:
            continue

    raise BancoErro(f"Data de referência inválida: {valor}")


def _normalizar_datetime_mysql(valor: Any, obrigatorio: bool = False) -> Optional[str]:
    if isinstance(valor, datetime):
        return valor.strftime("%Y-%m-%d %H:%M:%S")

    texto = str(valor or "").strip()
    if not texto:
        if obrigatorio:
            raise BancoErro("Data/hora obrigatória vazia")
        return None

    for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(texto, formato).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

    raise BancoErro(f"Data/hora inválida: {valor}")


def _normalizar_numero(valor: Any) -> Optional[float]:
    if valor is None or valor == "":
        return None
    try:
        return float(str(valor).replace(",", "."))
    except ValueError as exc:
        raise BancoErro(f"Valor numérico inválido: {valor}") from exc


def criar_tabela_vazao_pira(conexao=None) -> None:
    """Cria a tabela de vazão/nível/chuva se ela ainda não existir."""
    conexao_criada = conexao is None
    if conexao is None:
        conexao = _abrir_conexao_banco()

    cursor = conexao.cursor()
    try:
        cursor.execute(SQL_CRIAR_TABELA_VAZAO_PIRA)
        conexao.commit()
    finally:
        cursor.close()
        if conexao_criada:
            conexao.close()


def salvar_vazao_pira(payload: Dict[str, Any]) -> int:
    """Salva o dict final da API na tabela vazao_pira e retorna quantos horários foram tratados."""
    dados = payload.get("dados") or {}
    if not dados:
        return 0

    estacao = payload.get("estacao") or "PCH_Pira_Montante"
    referencia = _normalizar_data_mysql(payload.get("referencia"))
    timezone_payload = payload.get("timezone") or "-03:00"
    especificacao = payload.get("especificacao") or {}
    status_lote = payload.get("status_lote") or {}

    unidade_nivel = especificacao.get("nivel", {}).get("unidade", "cm")
    unidade_chuva = especificacao.get("chuva", {}).get("unidade", "mm")
    unidade_vazao = especificacao.get("vazao", {}).get("unidade", "m3/s")
    processado = 1 if status_lote.get("processado", True) else 0
    latencia = status_lote.get("latencia_max_segundos")
    if latencia is not None:
        try:
            latencia = int(latencia)
        except (TypeError, ValueError) as exc:
            raise BancoErro(f"Latência inválida: {latencia}") from exc

    registros = []
    for data_hora, leitura in dados.items():
        registros.append((
            estacao,
            referencia,
            timezone_payload,
            _normalizar_datetime_mysql(data_hora, obrigatorio=True),
            _normalizar_numero(leitura.get("nivel")),
            _normalizar_numero(leitura.get("chuva")),
            _normalizar_numero(leitura.get("vazao")),
            _normalizar_datetime_mysql(leitura.get("recebido_em")),
            unidade_nivel,
            unidade_chuva,
            unidade_vazao,
            processado,
            latencia,
        ))

    conexao = _abrir_conexao_banco()
    cursor = conexao.cursor()
    try:
        criar_tabela_vazao_pira(conexao)
        cursor.executemany(SQL_UPSERT_VAZAO_PIRA, registros)
        conexao.commit()
        return len(registros)
    except Exception:
        conexao.rollback()
        raise
    finally:
        cursor.close()
        conexao.close()


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


def consultar_e_salvar_estacao(
    station_id: str,
    data_date: str,
    send_date: str = "",
    register_date: str = "",
    send_status: str = "",
) -> Dict[str, Any]:
    """Consulta a estação e persiste o lote atual na tabela vazao_pira."""
    resultado = consultar_estacao(
        station_id=station_id,
        data_date=data_date,
        send_date=send_date,
        register_date=register_date,
        send_status=send_status,
    )
    registros_salvos = salvar_vazao_pira(resultado)
    resultado.setdefault("status_lote", {})["registros_salvos"] = registros_salvos
    return resultado


def _normalizar_data_final(data_final: Optional[Any]) -> date:
    if data_final is None:
        return date.today()
    if isinstance(data_final, datetime):
        return data_final.date()
    if isinstance(data_final, date):
        return data_final
    return datetime.strptime(str(data_final), "%Y-%m-%d").date()


def consultar_e_salvar_ultimos_dias(
    station_id: str = "200",
    dias: int = 30,
    data_final: Optional[Any] = None,
    send_status: str = "",
) -> Dict[str, Any]:
    """Consulta e salva a janela diária, incluindo data_final e os dias anteriores."""
    if dias <= 0:
        raise ValueError("dias deve ser maior que zero")

    fim = _normalizar_data_final(data_final)
    inicio = fim - timedelta(days=dias - 1)
    resumo = {
        "tabela": "vazao_pira",
        "data_inicio": inicio.isoformat(),
        "data_final": fim.isoformat(),
        "dias_processados": 0,
        "total_registros": 0,
        "erros": [],
    }

    for offset in range(dias):
        dia = inicio + timedelta(days=offset)
        data_str = dia.isoformat()
        print(f"[VAZAO] Consultando {data_str}", flush=True)

        try:
            resultado = consultar_e_salvar_estacao(
                station_id=station_id,
                data_date=data_str,
                send_date=data_str,
                register_date="",
                send_status=send_status,
            )
        except Exception as exc:
            erro = {"referencia": data_str, "erro": str(exc)}
            resumo["erros"].append(erro)
            print(f"[VAZAO] Erro em {data_str}: {exc}", flush=True)
            continue

        registros = resultado.get("status_lote", {}).get("registros_salvos", 0)
        resumo["dias_processados"] += 1
        resumo["total_registros"] += registros
        print(f"[VAZAO] {data_str}: {registros} registros salvos", flush=True)

    return resumo


# -------------------------------------------------------------------
# EXECUÇÃO
# -------------------------------------------------------------------
if __name__ == "__main__":
    resumo = consultar_e_salvar_ultimos_dias(
        station_id="200",
        dias=30,
    )

    print(json.dumps(resumo, indent=2, ensure_ascii=False))


    '''

    '''
