# API Modbus TCP - Documentação

## Descrição

Esta API permite a leitura e escrita de registradores em CLPs via protocolo Modbus TCP, utilizando FastAPI. Suporta operações de leitura de dados e escrita de comandos específicos.

---

## Como executar

1. **Pré-requisitos:**
   - Python 3.8+
   - Instale as dependências:
     ```bash
     pip install -r requirements.txt
     ```
2. **Executando a API:**
   ```bash
   python interface.py
   ```
   A API será iniciada no endereço e porta definidos pelas variáveis de ambiente `API_HOST` e `API_PORT` (padrão: 0.0.0.0:8010).

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
- **Resposta (erro):**
  ```json
  {
    "data": null,
    "status": "error",
    "message": "Mensagem de erro"
  }
  ```

### 2. `POST /writeCLP/{tipo}`

- **Descrição:** Escreve valores em registradores do CLP (atualmente apenas para reset de alarmes automáticos).
- **Parâmetro de rota:**
  - `tipo`: `reset_alarmes_automatico`
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
- **Resposta (erro):**
  ```json
  {
    "data": null,
    "status": "error",
    "message": "Mensagem de erro"
  }
  ```

---

## Observações

- Os campos de conexão (`ip`, `port`, `timeout`) são obrigatórios.
- Os nomes das variáveis em `registers` identificam as leituras/escritas no retorno.
- Cada registro deve indicar o tipo (`REAL`, `INT`, `BOOLEAN`) e pode trazer opções extras:
  - `offset`: ajuste aplicado ao endereço (padrão `-1`).
  - `converter`: como combinar os dois registradores para valores `REAL` (`default`, `word_order`, `endianness`, `byte_order`, `swap`).
- Em caso de erro de conexão ou leitura/escrita, a resposta terá `status: error` e uma mensagem explicativa.

---

## Ambiente

- Assegure que o CLP esteja acessível via rede e que as portas estejam liberadas.
- Para ambientes de desenvolvimento, teste com CLPs simulados ou dispositivos reais.

---

## Contato

Dúvidas ou sugestões: [Seu Nome ou Email]
