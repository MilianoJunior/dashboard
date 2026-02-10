# Lógica de Consultas ao Banco de Dados — `datas.py`

## Estrutura Geral

Cada usina tem sua própria tabela MySQL (ou par de tabelas para multi-UG). Os nomes das colunas variam entre usinas, mas são **padronizados internamente** via mapeamento definido no YAML (`usuarios_usinas.yaml`).

---

## Tipos de Tabela

| Tipo | Usinas | Tabela(s) |
|------|--------|-----------|
| **Tabela única** | Aparecida, FAE, Picadas-Altas | `cgh_aparecida`, `cgh_fae`, `cgh_picadas_altas` |
| **Multi-tabela** (1 por UG) | Pedras, Hoppen | `pch_pedras_ug01/ug02`, `cgh_hoppen_ug01/ug02` |

---

## Mapeamento de Colunas (padronizado → real)

O código trabalha com nomes **padronizados** (`energia_ug01`, `nivel_montante`) e converte para os nomes **reais** do banco na hora da query.

`convert_padronizado_to_real()` faz essa tradução. Para multi-tabela, usa apenas o sub-dicionário `ug01`.

**Exemplos:**

| Usina | Padronizado | Real no banco |
|-------|-------------|---------------|
| Aparecida | `energia_ug01` | `acumulador_energia` |
| FAE | `energia_ug01` | `ug01_acumulador_energia` |
| Pedras (ug01) | `energia_ug01` | `acum_energia` |
| Picadas | `nivel_montante` | `nivel_montante` |
| FAE | `nivel_montante` | `ug01_nivel_agua` |
| Pedras (ug01) | `nivel_montante` | `niv_mont_grade` |

---

## Fluxo Principal de Consultas

### 1. `get_db_data(data_inicial, data_final)`
Busca dados brutos para o dashboard interativo.

- **Tabela única:** query direta com alias (`SELECT col_real AS col_padrao`)
- **Multi-tabela:** busca cada UG separadamente, arredonda `data_hora` por minuto, faz `pd.merge(..., on='data_hora', how='outer')`
- Resultado salvo em `session_state['dados']` e `session_state['dados_geral']`

### 2. `get_ultimos_180_dias_mensal()` → Cards de energia
Busca 180 dias, calcula produção mensal acumulada.

- Usa `_get_dados_mensais_cached()` com `st.cache_data(ttl=6h)`
- Multi-tabela: busca **apenas UG01** (não faz merge)
- Chama `calcular_energia_acumulada(df, cols, 'M')`
- Gera coluna `data_hora` com mês/ano em português

### 3. `get_grafico_energia(periodo, data_inicial, data_final)` → Gráfico de barras
- Cache de 5 minutos via `_get_grafico_energia_cached()`
- Períodos: `'D'` (diário), `'M'` (mensal), `'H'` (horário)
- Multi-tabela: apenas UG01

### 4. `get_grafico_nivel(periodo)` → Gráfico de linha
- Cache de 5 minutos via `_get_grafico_nivel_cached()`
- Busca apenas colunas de nível (não energia)
- Janela reduzida: 7 dias para horário, 30 dias para diário
- Resample: `'M'→'D'` (média diária), `'D'→'h'` (média horária)
- Forward fill em valores None

### 5. `get_names_all_columns()` → Exploração livre
- Cache de 24h
- Query em `INFORMATION_SCHEMA.COLUMNS`

### 6. `fetch_dados_graficos()` / `fetch_dados_graficos_tabela()` → Gráfico exploratório
- Sem cache
- Recebe colunas selecionadas pelo usuário
- Query com `BETWEEN` no intervalo

---

## Tratamentos e Exceções

### `tratamento_df(df)`
Aplicado em **toda** query retornada.

1. Colunas string que são numéricas → convertidas para `float`
2. Filtra linhas onde **todas** colunas numéricas são `>= 10` (remove registros com zeros/lixo do CLP)

### `tratamento_aparecida(df)` — Correção de reset do acumulador
Aplicado **apenas** em `cgh_aparecida`.

**Problema:** O acumulador de energia do CLP resetou em `2025-10-14 03:35:00`, criando uma queda brusca nos valores.

**Correção:**
1. Filtra registros a partir do threshold (`2025-10-14 03:35`)
2. Calcula `np.diff()` no vetor de energia
3. Encontra a primeira queda (`diff < 0`)
4. Soma offset fixo de `9971.39 MWh` em todos os registros **a partir da queda**
5. Retorna `(df_corrigido, contagem_antes_da_queda, info_debug)`

Se não houver queda, retorna o df inalterado.

### Filtro de valor `103.00` em `calcular_energia_acumulada()`
Remove linhas onde qualquer coluna de energia tem valor exatamente `103.00` — valor espúrio recorrente enviado pelo CLP em condição de erro.

### Cálculo de produção por `diff()`
A energia é **acumulada** (totalizador do CLP). A produção real é calculada por `df[col].diff()`:
- **Diário (`'D'`):** agrupa por `data_hora.dt.date`, pega `.last()`, calcula diff entre dias
- **Mensal (`'M'`):** agrupa por `ano_mes` (formato `YYYY-MM`), pega `.last()`, calcula diff entre meses
  - Se < 6 meses de dados, insere mês anterior com valor 0 para o diff funcionar
- **Horário (`'H'`):** arredonda para hora (`dt.floor('h')`), pega `.last()`, calcula diff entre horas

---

## Cache

| Função | TTL | Motivo |
|--------|-----|--------|
| `_get_dados_mensais_cached` | 6h | Dados mensais mudam pouco |
| `_get_grafico_nivel_cached` | 5min | Nível precisa ser recente |
| `_get_grafico_energia_cached` | 5min | Energia precisa ser recente |
| `_get_names_all_columns_cached` | 24h | Schema raramente muda |

---

## Resumo do fluxo de dados

```
YAML (config)          →  mapeamento padronizado ↔ real
                            ↓
MySQL (tabelas CLP)    →  query com nomes reais + alias
                            ↓
tratamento_df()        →  conversão numérica + filtro >= 10
                            ↓
tratamento_aparecida() →  correção offset (só Aparecida)
                            ↓
calcular_energia_acumulada() → diff() por período (D/M/H)
                                 + filtro 103.00
                            ↓
session_state / gráficos
```
