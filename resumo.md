# Resumo do Projeto — Dashboard EngeGOM

## Visao Geral

Dashboard web para monitoramento de usinas hidreletricas (CGH/PCH), desenvolvido com **Streamlit** e deploy via **Railway**. O sistema permite que operadores acompanhem em tempo real a geracao de energia, niveis de reservatorio e variaveis de telemetria de cada usina.

---

## Usinas Monitoradas

| Codigo            | Tipo | UGs | Tabela(s) no Banco               |
|-------------------|------|-----|-----------------------------------|
| CGH-APARECIDA     | CGH  | 1   | `cgh_aparecida`                   |
| CGH-FAE           | CGH  | 2   | `cgh_fae`                         |
| PCH-PEDRAS        | PCH  | 2   | `pch_pedras_ug01`, `pch_pedras_ug02` |
| CGH-PICADAS-ALTAS | CGH  | 2   | `cgh_picadas_altas`               |
| CGH-HOPPEN        | CGH  | 2   | `cgh_hoppen_ug01`, `cgh_hoppen_ug02` |
| PCH-PIRA          | PCH  | -   | (apenas configuracao parcial)     |

---

## Arquitetura

O projeto segue um padrao **MVC** (Model-View-Controller):

```
main.py                    # Ponto de entrada — inicializa sessao, login, menu e layout
libs/
  controllers/
    auth.py                # Autenticacao por usina (usuario fixo + senha por usina)
    config_controller.py   # Carrega config YAML com definicao das usinas
    data_controller.py     # Orquestra chamadas a API externa (producao, nivel, sensores)
    api_controller.py      # Cliente HTTP para a API ENGESEP (POST/GET com urllib)
  models/
    db.py                  # Classe Database — conexao MySQL direta
    datas.py               # Queries ao banco, tratamento de dados, cache de graficos
    calculos.py            # Calculo de energia acumulada (diaria, mensal, horaria)
  views/
    componentes.py         # Componentes visuais: cards, graficos Plotly, login, menu, footer
    pages.py               # Monta o layout principal do dashboard
  utils/
    decorators.py          # Decorator de desempenho (mede tempo) e tratamento de erros
    db_utils.py            # Inicializa conexao DB no session_state
config/
  usuarios_usinas.yaml     # Mapeamento de usinas: tabelas, colunas, credenciais, niveis
  usinas_cont.yaml         # Contador de acessos por usina
assets/                    # Logos, imagens de login, CSS customizado
```

---

## Fontes de Dados

O dashboard opera com **duas fontes de dados** (em transicao):

1. **API ENGESEP** (fonte principal no branch atual) — API REST externa que abstrai o banco MySQL, faz resample automatico, filtra outliers e normaliza nomes de colunas. Endpoints utilizados:
   - `POST /producao-acumulada` — geracao por periodo (H/D/M)
   - `POST /grupo-usina` — variaveis de um grupo (ex: hidraulica para niveis)
   - `GET /grupos/{usina}` — lista grupos e variaveis disponiveis
   - `POST /sensor-usina` — historico de uma variavel especifica

2. **Acesso direto ao MySQL** (codigo legado em `datas.py`) — consultas SQL diretas ao banco de cada usina. Ainda presente no codigo mas sendo substituido pelas chamadas via API.

---

## Fluxo Principal

1. **Login** — Usuario seleciona a usina e insere a senha. Sessao persistida via cookies (validade 10 dias).
2. **Carregamento de dados** — `carregar_dados()` dispara em paralelo (ThreadPoolExecutor):
   - Cards de geracao mensal (ultimos meses)
   - Grafico de producao de energia (por periodo selecionado)
   - Grafico de nivel do reservatorio
3. **Renderizacao** — O dashboard exibe:
   - Cards com MWh gerado por mes + calculadora de receita (valor do MWh x participacao)
   - Grafico de barras de producao de energia (Plotly)
   - Grafico de linha de nivel do reservatorio com linha de vertimento
   - Analise personalizada: selecao livre de variaveis via API
4. **Exportacao** — Download de dados em CSV e Excel

Eu gostaria de acrescentar:
um Gauge por Unidade Geradora, que vai mostrar a potência ativa instantânea em tempo real, o valor máximo 
do gauge vai ser o valor de potência nominal de projeto e a cor do gauge vai mudar de acordo com a potência ativa instantânea.
Talvez tenhamos que diminuir a fonte ou mudar os espaçamentos, mas esses componentes devem ficar em uma coluna ou linha e manter
a visualização em pagina unica. 

---

## Funcionalidades

- **Calculadora de receita**: valor do MWh x percentual de participacao sobre a geracao
- **Filtro por periodo**: hora, diario ou mensal, com selecao de datas
- **Nivel de vertimento**: linha de referencia no grafico de nivel (configuravel por usina)
- **Analise personalizada**: consulta exploratoria de qualquer variavel disponivel na API
- **Autenticacao por usina**: cada usina tem senha propria, com persistencia via cookie
- **Contador de acessos**: registra numero de logins por usina em `usinas_cont.yaml`

---

## Stack Tecnologica

| Camada        | Tecnologia                              |
|---------------|-----------------------------------------|
| Frontend      | Streamlit 1.52, Plotly, CSS customizado |
| Backend       | Python 3.x, pandas, numpy              |
| Banco         | MySQL (mysql-connector-python)          |
| API externa   | ENGESEP API (REST, JSON)                |
| Deploy        | Railway (auto-deploy via GitHub push)   |
| Config        | YAML, python-dotenv (.env)              |
| Exportacao    | XlsxWriter, openpyxl, fpdf             |

---

## Observacoes

- O deploy e automatico: cada push para o branch vinculado ao Railway vai direto para producao.
- O arquivo `config/usuarios_usinas.yaml` contem mapeamentos criticos (colunas do banco variam por usina/fabricante do CLP) e nao deve ser alterado sem validacao.
- O codigo esta em transicao de acesso direto ao banco para uso exclusivo da API ENGESEP, mantendo codigo legado em `datas.py`.
- Usinas com 2 UGs e tabelas separadas (Pedras, Hoppen) exigem merge de dados por `data_hora`.

'''
Tenho dois bancos de dados que preciso fazer um sicronização, todas as tabelas do mysql railway devem ser criadas no gcloud e todos os dados devem ser copiado para lá, mas no banco do gcloud eu
já comecei a fazer a migração, então primeiro eu preciso ver:


Pode listar todas as tabelas do gcloud?
'''
