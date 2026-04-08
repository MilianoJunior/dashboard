# API Modbus TCP - Documentação

## Descrição

Esta API permite a leitura e escrita de registradores em CLPs via protocolo Modbus TCP, utilizando FastAPI. Suporta operações de leitura de dados e escrita de comandos específicos, além de gerenciamento de conexões ativas.

---

## Como executar

1. **Pré-requisitos:**
   - Python 3.8+
   - Instale as dependências:
     ```bash
     pip install -r requirements.txt
     ```
2. **Executando a API padrão:**

   ```bash
   python interface.py
   ```

   A API será iniciada no endereço e porta definidos pelas variáveis de ambiente `API_HOST` e `API_PORT` (padrão: 0.0.0.0:8010).

3. **Executando para PCH-PIRA (Exceção de INPUT):**
   A usina PCH-PIRA requer a leitura de **Input Registers** em vez de Holding Registers padrão para alguns dados. Portanto, ela utiliza a API específica:
   ```bash
   python interfacePira.py
   ```

---

## Rotas Disponíveis

### 1. `POST /readCLP/{tipo}`

- **Descrição:** Lê valores de registradores do CLP.
- **Parâmetro de rota:**
  - `tipo`: `leituras` ou `alarmes`
- **Body (JSON):**
  ```json
  {
    "conexao": {
      "ip": "192.168.0.10",
      "port": 502,
      "timeout": 10.0
    },
    "registers": {
      "nivel_montante": [
        13519,
        "REAL",
        { "offset": -1, "converter": "word_order" }
      ],
      "potencia_ativa": [13407, "INT", { "offset": -1 }],
      "religamento": [12321, "BOOLEAN", { "offset": -1 }]
    }
  }
  ```

  - Cada registro é definido como `[endereco, tipo, {opções}]`.
  - `offset` é opcional (padrão `-1`).
  - `converter` é opcional e pode assumir os valores `default`, `word_order`, `endianness`, `byte_order`, `swap`.
- **Resposta (sucesso):**
  ```json
  {
    "data": {
      "nivel_montante": 404.12,
      "potencia_ativa": 1812,
      "religamento": true
    },
    "status": "success",
    "message": null
  }
  ```

### 2. `POST /writeCLP/{tipo}`

- **Descrição:** Escreve valores em registradores do CLP.
- **Parâmetro de rota:**
  - `tipo`: `reset_alarmes_automatico` ou `escritas`
- **Body (JSON):**
  ```json
  {
    "conexao": {
      "ip": "192.168.0.10",
      "port": 502,
      "timeout": 10.0
    },
    "registers": {
      "reset_alarme": [3001, "BOOLEAN", true, { "offset": -1 }]
    }
  }
  ```

  - Cada item de escrita segue o formato `[endereco, tipo, valor, {opções}]` com os mesmos parâmetros de offset/converter utilizados na leitura.
- **Resposta (sucesso):**
  ```json
  {
    "data": {
      "reset_alarme": null
    },
    "status": "success",
    "message": null
  }
  ```

### 3. `GET /listConnections`

- **Descrição:** Lista todas as conexões Modbus ativas no servidor.
- **Resposta (sucesso):**
  ```json
  {
    "data": {
      "active_connections": [
        {
          "connection": "192.168.0.10:502",
          "connected": true,
          "last_used": 1712613456.12,
          "idle_time_seconds": 15.34
        }
      ]
    },
    "status": "success",
    "message": "1 conexões ativas encontradas"
  }
  ```

### 4. `POST /closeConnections`

- **Descrição:** Encerra forçadamente todas as conexões Modbus ativas e libera recursos.
- **Resposta (sucesso):**
  ```json
  {
    "data": {
      "closed_connections": ["192.168.0.10:502"]
    },
    "status": "success",
    "message": "1 conexões fechadas com sucesso"
  }
  ```

### 5. `GET /diagnostics`

- **Descrição:** Retorna o estado de saúde do sistema, detalhando conexões ativas e listando das últimas linhas de log.
- **Parâmetros de query:**
  - `log_lines` (opcional): Quantidade de linhas retirasd do fim do log que serão retornadas. Padrão: 50.
- **Resposta (sucesso):**
  ```json
  {
    "data": {
      "server_timestamp": 1712613500.0,
      "active_connections_count": 1,
      "connections": [],
      "logs": [
        "2026-04-08 11:45:00 [INFO] Conexão Modbus ativa: 192.168.0.10:502"
      ]
    },
    "status": "success",
    "message": "Diagnóstico realizado com sucesso"
  }
  ```

---

## Exceção PCH-PIRA (Input Registers)

No script `interfacePira.py`, foi inserida uma variação nativa para ler **Input Registers** ao invés de **Holding Registers**.
Para utilizar essa leitura exclusiva de PCH-PIRA, o `tipo` fornecido no dicionário de `registers` deve conter a string `INPUT`. Exemplos aceitos:

- `"REAL INPUT"`
- `"INT INPUT"`

A lógica principal em `interfacePira.py` faz a validação `is_input = "INPUT" in tipo`, e em seguida utiliza o `client.read_input_registers` para buscar os dados corretamente, agrupando-os por tipo de registro, evitando requisições incorretas de blocos combinados entre holding/input registers.

---

## Observações Gerais

- Os campos de conexão (`ip`, `port`, `timeout`) são obrigatórios.
- Os nomes das variáveis em `registers` identificam as leituras/escritas no retorno.
- Registros suportados (`REAL`, `INT`, `BOOLEAN`) via Holding Registers ou Input Registers (na PCH-PIRA). Opções limitadas a `offset` e `converter`.
- Em caso de erro de conexão ou leitura/escrita, a resposta terá `status: error` e uma mensagem explicativa.
