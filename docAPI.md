# ⚡ ENGESEP API - Monitoramento e Telemetria

API para consulta de dados históricos, telemetria e cálculo de produção de energia para usinas hidrelétricas.

Baseada no mapeamento `config/usinas.json`, a API normaliza nomes de colunas e tabelas para que o cliente não precise conhecer a estrutura do banco.

---

## 📖 Guia Rápido de Uso

### Passo 1 — Descubra as usinas disponíveis

```
GET /usinas
```

### Passo 2 — Veja os grupos e variáveis da usina

```
GET /grupos/CGH-APARECIDA
```

### Passo 3 — Consulte os dados

Use o **nome do grupo** (`POST /grupo-usina`) ou o **alias da variável** (`POST /sensor-usina`) retornados no passo anterior.

> **Formato de data obrigatório:** `DD/MM/YYYY HH:mm`

---

## 🔑 Conceitos Importantes

### Usinas com 1 UG vs 2 UGs

| Tipo      | Exemplo         | Comportamento                                                                   |
| :-------- | :-------------- | :------------------------------------------------------------------------------ |
| **1 UG**  | `CGH-APARECIDA` | Todas as variáveis retornam com prefixo `UG-01`                                 |
| **2 UGs** | `PCH-PEDRAS`    | As variáveis de cada UG vêm juntas na mesma resposta: `UG-01 ...` e `UG-02 ...` |

### Resolução Automática

O cliente envia apenas as datas. A API decide o intervalo de resample:

| Intervalo solicitado | Resolução aplicada   |
| :------------------- | :------------------- |
| ≤ 1 hora             | 1 min (dados brutos) |
| ≤ 1 dia              | 15 min               |
| > 1 dia              | 30 min               |

### Filtro de Outliers (IQR)

Valores fora de `[Q1 - 1.5×IQR, Q3 + 1.5×IQR]` são substituídos pelo último valor válido (`ffill`). Nenhum registro é removido. Grupos do tipo `status` não são filtrados.

---

## 📡 Endpoints

### `GET /usinas`

Lista todas as usinas configuradas.

**Resposta:**

```json
{
  "usinas_disponiveis": [
    { "codigo": "CGH-APARECIDA", "descricao": "CGH Aparecida - 1 UG" },
    { "codigo": "CGH-FAE", "descricao": "CGH FAE - 2 UGs" },
    { "codigo": "PCH-PEDRAS", "descricao": "PCH Pedras - 2 UGs" },
    { "codigo": "CGH-PICADAS-ALTAS", "descricao": "CGH Picadas Altas - 2 UGs" },
    { "codigo": "CGH-HOPPEN", "descricao": "CGH Hoppen - 2 UGs" }
  ]
}
```

---

### `GET /grupos/{usina}`

Retorna os grupos disponíveis e seus aliases. **Use os aliases retornados aqui como parâmetro nas consultas.**

#### Exemplo: Usina com 1 UG (`CGH-APARECIDA`)

```
GET /grupos/CGH-APARECIDA
```

```json
{
  "status": ["UG-01 Status"],
  "energia": ["UG-01 Energia Acumulada"],
  "eletrica": [
    "UG-01 Tensão Fase A",
    "UG-01 Tensão Fase B",
    "UG-01 Tensão Fase C",
    "UG-01 Corrente Fase A",
    "UG-01 Corrente Fase B",
    "UG-01 Corrente Fase C",
    "UG-01 Tensão Excitação",
    "UG-01 Corrente Excitação",
    "UG-01 Frequência"
  ],
  "potencia": [
    "UG-01 Potência Ativa",
    "UG-01 Potência Reativa",
    "UG-01 Potência Aparente",
    "UG-01 Fator de Potência"
  ],
  "mecanica": [
    "UG-01 Distribuidor",
    "UG-01 Velocidade",
    "UG-01 Posição Rotor",
    "UG-01 Horímetro"
  ],
  "hidraulica": ["Nível Montante", "Nível Jusante", "UG-01 Vazão Turbina"],
  "pressoes": ["UG-01 Pressão Óleo UHLM", "UG-01 Pressão Óleo UHRV"],
  "temperaturas": [
    "UG-01 Temp. Óleo UHLM",
    "UG-01 Temp. Óleo UHRV",
    "UG-01 Temp. Mancal Casquilho Combinado",
    "UG-01 Temp. Enrolamento Fase A",
    "..."
  ]
}
```

#### Exemplo: Usina com 2 UGs (`PCH-PEDRAS`)

```
GET /grupos/PCH-PEDRAS
```

```json
{
  "status": ["UG-01 Status", "UG-02 Status"],
  "energia": ["UG-01 Energia Acumulada", "UG-02 Energia Acumulada"],
  "potencia": [
    "UG-01 Potência Ativa",
    "UG-01 Potência Reativa",
    "UG-01 Potência Aparente",
    "UG-01 Fator de Potência",
    "UG-02 Potência Ativa",
    "UG-02 Potência Reativa",
    "UG-02 Potência Aparente",
    "UG-02 Fator de Potência"
  ],
  "mecanica": [
    "UG-01 Distribuidor",
    "UG-01 Rotor",
    "UG-01 Velocidade",
    "UG-01 Horímetro",
    "UG-02 Distribuidor",
    "UG-02 Rotor",
    "UG-02 Velocidade",
    "UG-02 Horímetro"
  ],
  "temperaturas": [
    "UG-01 Temp. Óleo UHLM",
    "UG-01 Temp. Enrolamento Fase A",
    "...",
    "UG-02 Temp. Óleo UHLM",
    "UG-02 Temp. Enrolamento Fase A",
    "..."
  ],
  "vibracao": [
    "UG-01 Vibração Eixo LA X",
    "UG-01 Vibração Eixo LA Y",
    "...",
    "UG-02 Vibração Eixo LA X",
    "UG-02 Vibração Eixo LA Y",
    "..."
  ]
}
```

> **Diferença principal:** Usinas com 2 UGs que possuem **tabelas separadas** (como `PCH-PEDRAS` → `pch_pedras_ug01` e `pch_pedras_ug02`) fazem merge automático dos dados por `data_hora` na resposta.

---

### `POST /sensor-usina`

Consulta o histórico de **uma única variável**.

#### Exemplo: 1 UG — Potência Ativa

**Request:**

```json
{
  "usina": "CGH-APARECIDA",
  "variavel": "UG-01 Potência Ativa",
  "data_inicio": "15/01/2026 08:00",
  "data_fim": "15/01/2026 09:00",
  "token": "seu_token"
}
```

**Response:** (intervalo ≤ 1h → resolução 1 min)

```json
{
  "usina": "CGH-APARECIDA",
  "variavel": "UG-01 Potência Ativa",
  "registros": 60,
  "dados": [
    { "data_hora": "2026-01-15T08:00:00", "UG-01 Potência Ativa": 125.4 },
    { "data_hora": "2026-01-15T08:01:00", "UG-01 Potência Ativa": 124.8 },
    { "data_hora": "2026-01-15T08:02:00", "UG-01 Potência Ativa": 126.1 },
    "..."
  ]
}
```

#### Exemplo: 2 UGs — Potência Ativa da UG-02

**Request:**

```json
{
  "usina": "PCH-PEDRAS",
  "variavel": "UG-02 Potência Ativa",
  "data_inicio": "15/01/2026 08:00",
  "data_fim": "15/01/2026 09:00",
  "token": "seu_token"
}
```

**Response:**

```json
{
  "usina": "PCH-PEDRAS",
  "variavel": "UG-02 Potência Ativa",
  "registros": 60,
  "dados": [
    { "data_hora": "2026-01-15T08:00:00", "UG-02 Potência Ativa": 310.2 },
    { "data_hora": "2026-01-15T08:01:00", "UG-02 Potência Ativa": 308.7 },
    "..."
  ]
}
```

> **Importante:** Para consultar a potência de ambas as UGs de uma vez, use `POST /grupo-usina` com `grupo: "potencia"`.

---

### `POST /grupo-usina`

Consulta **todas as variáveis de um grupo** de uma vez.

#### Exemplo: 1 UG — Grupo `potencia` (CGH-APARECIDA)

**Request:**

```json
{
  "usina": "CGH-APARECIDA",
  "grupo": "potencia",
  "data_inicio": "15/01/2026 00:00",
  "data_fim": "16/01/2026 00:00",
  "token": "seu_token"
}
```

**Response:** (intervalo = 1 dia → resolução 15 min)

```json
{
  "usina": "CGH-APARECIDA",
  "grupo": "potencia",
  "registros": 96,
  "dados": [
    {
      "data_hora": "2026-01-15T00:00:00",
      "UG-01 Potência Ativa": 120.5,
      "UG-01 Potência Reativa": 18.3,
      "UG-01 Potência Aparente": 121.9,
      "UG-01 Fator de Potência": 0.989
    },
    {
      "data_hora": "2026-01-15T00:15:00",
      "UG-01 Potência Ativa": 118.2,
      "UG-01 Potência Reativa": 17.9,
      "UG-01 Potência Aparente": 119.6,
      "UG-01 Fator de Potência": 0.988
    },
    "..."
  ]
}
```

#### Exemplo: 2 UGs — Grupo `potencia` (PCH-PEDRAS)

**Request:**

```json
{
  "usina": "PCH-PEDRAS",
  "grupo": "potencia",
  "data_inicio": "15/01/2026 00:00",
  "data_fim": "16/01/2026 00:00",
  "token": "seu_token"
}
```

**Response:** (dados das duas UGs na mesma linha temporal)

```json
{
  "usina": "PCH-PEDRAS",
  "grupo": "potencia",
  "registros": 96,
  "dados": [
    {
      "data_hora": "2026-01-15T00:00:00",
      "UG-01 Potência Ativa": 305.1,
      "UG-01 Potência Reativa": 42.3,
      "UG-01 Potência Aparente": 308.0,
      "UG-01 Fator de Potência": 0.991,
      "UG-02 Potência Ativa": 298.7,
      "UG-02 Potência Reativa": 39.8,
      "UG-02 Potência Aparente": 301.3,
      "UG-02 Fator de Potência": 0.991
    },
    {
      "data_hora": "2026-01-15T00:15:00",
      "UG-01 Potência Ativa": 302.4,
      "UG-01 Potência Reativa": 41.0,
      "UG-01 Potência Aparente": 305.2,
      "UG-01 Fator de Potência": 0.991,
      "UG-02 Potência Ativa": 300.1,
      "UG-02 Potência Reativa": 40.5,
      "UG-02 Potência Aparente": 302.8,
      "UG-02 Fator de Potência": 0.991
    },
    "..."
  ]
}
```

> **Observe:** Na `PCH-PEDRAS`, cada UG tem sua própria tabela no banco (`pch_pedras_ug01`, `pch_pedras_ug02`). A API faz o merge automaticamente por `data_hora` e retorna tudo unificado.

---

### `POST /tabela-usina`

Retorna **todas as colunas** de todas as tabelas da usina. Sem filtro de outliers, sem resample. Ideal para dump/auditoria.

**Request:**

```json
{
  "usina": "CGH-APARECIDA",
  "data_inicio": "15/01/2026 08:00",
  "data_fim": "15/01/2026 08:05",
  "token": "seu_token"
}
```

**Response:**

```json
{
  "usina": "CGH-APARECIDA",
  "registros": 5,
  "tabelas": ["cgh_aparecida"],
  "dados": [
    {
      "data_hora": "2026-01-15T08:00:00",
      "id": 12401,
      "status": 1,
      "potencia_ativa": 125.4,
      "tensao_fase_A": 4180.0,
      "nivel_montante": 512.3,
      "_tabela": "cgh_aparecida"
    },
    "..."
  ]
}
```

> **Nota:** Os nomes das colunas na resposta do `/tabela-usina` são os nomes **originais do banco** (sem aliases). Use os outros endpoints para obter os nomes amigáveis.

---

### `POST /producao-acumulada`

Calcula geração de energia por período.

**Request:**

```json
{
  "usina": "CGH-APARECIDA",
  "data_inicio": "01/01/2026 00:00",
  "data_fim": "03/01/2026 23:59",
  "periodo": "D",
  "token": "seu_token"
}
```

- `periodo`: `"H"` (Hora) · `"D"` (Dia) · `"M"` (Mês)

---

### `GET /health`

```json
{ "status": "operacional", "database": "conectado" }
```

---

## 📚 Referência de Grupos por Usina

| Grupo        | CGH-APARECIDA | CGH-FAE | PCH-PEDRAS | CGH-PICADAS-ALTAS | CGH-HOPPEN |
| :----------- | :-----------: | :-----: | :--------: | :---------------: | :--------: |
| status       |      ✅       |   ✅    |     ✅     |        ✅         |     ✅     |
| energia      |      ✅       |   ✅    |     ✅     |        ✅         |     ✅     |
| eletrica     |      ✅       |   ✅    |     ✅     |        ✅         |     ✅     |
| potencia     |      ✅       |   ✅    |     ✅     |        ✅         |     ✅     |
| mecanica     |      ✅       |   ✅    |     ✅     |        ✅         |     ✅     |
| hidraulica   |      ✅       |   ✅    |     ✅     |        ✅         |     ✅     |
| pressoes     |      ✅       |   ✅    |     ✅     |        ✅         |     ✅     |
| temperaturas |      ✅       |   ✅    |     ✅     |        ✅         |     ✅     |
| vibracao     |       —       |   ✅    |     ✅     |         —         |     —      |
| diversos     |       —       |    —    |     ✅     |        ✅         |     —      |

---

## ⚙️ Configuração Local

### Pré-requisitos

- Python 3.10+
- MySQL Database

### Instalação

```bash
git clone <url-repo>
cd engesepAPI
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Variáveis de Ambiente (`.env`)

```env
MYSQLHOST=localhost
MYSQLUSER=root
MYSQLPASSWORD=sua_senha
MYSQLDATABASE=nome_do_banco
MYSQLPORT=3306
API_TOKEN=seu_token_seguro
```

### Executar

```bash
uvicorn main:app --reload
```

Swagger: `http://engesepapi-production.up.railway.app/docs`
