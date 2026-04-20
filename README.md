# Dashboard EngeGOM

Dashboard web para monitoramento operacional de usinas hidrelétricas (CGH/PCH), desenvolvido pela EngeGOM.

## Visão Geral

Aplicação Flask + Flask-SocketIO que exibe em tempo real e historicamente o status das usinas:

- **Gauges de potência** de cada Unidade Geradora (UG), com status e percentual de carga
- **Nível de montante** (nível d'água a montante da barragem)
- **Gráficos de produção de energia** (horária, diária e mensal)
- **Gráficos de nível** com linha de vertimento

Os dados históricos vêm de uma API REST externa (`/producao-acumulada`, `/grupo-usina`, `/sensor-usina`). Os dados em tempo real são lidos via API Modbus/CLP e enviados ao frontend por WebSocket. O projeto segue um padrão de interface com tailwindcss, atualizações in-place e responsividade.

## Experiência de Monitoramento em Tempo Real

O frontend foi projetado para transmitir ao operador a sensação de "sistema vivo":

- **Live Dot**: ponto verde pulsante ao lado do título "Resumo Tempo Real", indicando que o sistema está ativo
- **Timestamp dinâmico**: contador regressivo ao lado do título mostrando "Atualizado às HH:MM:SS - há Xs", atualizado a cada segundo
- **Efeito odômetro**: valores numéricos (percentual, potência, nível montante) rolam suavemente do valor antigo ao novo com interpolação ease-out cubic (800ms)
- **Transição suave nos arcos**: as barras dos gauges SVG deslizam via CSS transition ao invés de saltar
- **Sparklines com curvas Bezier**: mini-gráficos de área em cada card de UG e no resumo, mostrando a tendência dos últimos ~15 minutos (até 50 pontos)
  - Curvas suaves via conversão Catmull-Rom para Bezier cúbico
  - Gradiente de área (cor da UG -> transparente) dando volume visual
  - Leading dot pulsante com glow SVG no ponto atual
  - UGs paradas (0%) recuam visualmente: cor cinza, opacidade reduzida, sem dot
- **Atualização in-place**: o DOM nunca é destruído/recriado nas atualizações via socket, permitindo que todas as animações CSS e JS funcionem

## Usinas Suportadas

| Código            | Tipo |
| ----------------- | ---- |
| PCH-PIRA          | PCH  |
| PCH-PEDRAS        | PCH  |
| CGH-APARECIDA     | CGH  |
| CGH-PICADAS-ALTAS | CGH  |
| CGH-FAE           | CGH  |
| CGH-HOPPEN        | CGH  |

O número de UGs é dinâmico por usina (1 a N). A paleta de cores é aplicada ciclicamente. Cada usina possui autenticação própria persistida via sessão/cookies.

## Estrutura do Projeto

```
dashboard.py                  # Entrypoint Flask + SocketIO
libs/
  routes/routes.py            # Rotas HTTP (/, /health, login)
  controllers/
    dashboard_controller.py   # Lógica de montagem dos dados do dashboard
  models/
    api_model.py              # Chamadas HTTP para API externa (produção, nível, sensor)
    consultas.py              # Consulta e normalização de dados (produção, nível)
    config_model.py           # Modelo de configuração (YAML)
    gauge_rt.py               # Lógica de gauges e status das UGs
    colors.py                 # Paleta centralizada de cores (UG_COLORS, NIVEL_COLORS)
    utils.py                  # Filtros de template e utilitários
  views/
    componentes/
      base.html               # Layout base (Tailwind, fontes, animações CSS)
      dashboard.html          # Skeleton de loading + carga assíncrona
      gauge_card.html         # Macro Jinja do card individual de UG
      gauge_grid.html         # Grid de gauges + resumo RT + sparklines + socket JS
      generation_chart.html   # Gráfico de produção empilhado
      reservoir_chart.html    # Gráfico de nível do reservatório
      header.html             # Cabeçalho com seletor de usina
      bottom_nav.html         # Navegação inferior
    servicos/
      connect.py              # WebSocket: leitura RT via Modbus e emissão periódica
  utils/
    decorators.py             # Decorador de desempenho e logging
    auth.py                   # Autenticação de rotas e usinas
config/
  usinas_dispositivos.json    # Configuração de dispositivos/registros Modbus por usina
  usuarios_usinas.yaml        # Mapeamento usuários x usinas
  usinas_cont.yaml            # Configuração de contabilização
assets/                       # Logos e recursos estáticos
tests/                        # Testes automatizados
```

## Arquitetura e Fluxo

```
Browser  <--WebSocket-->  Flask-SocketIO  <--HTTP/Modbus-->  API CLP
Browser  <--HTTP GET-->   Flask Routes    <--HTTP POST-->    API REST externa
```

1. O usuário acessa a página de `/login`, autentica com as credenciais da usina e é redirecionado para `/`.
2. Acessando `/`, o usuário recebe o skeleton de loading inicial (`dashboard.html`).
3. O JS do skeleton faz um fetch assíncrono para `/api/dashboard` que retorna os dados históricos renderizados.
4. O SocketIO inicia a emissão periódica (~15-20s) lendo dados em tempo real de cada UG via API Modbus.
5. O frontend atualiza gauges, sparklines e resumo em tempo real sem reload da página.

## Paleta de Cores

Definida em `libs/models/colors.py` (fonte única de verdade):

| Índice | Cor       | Uso             |
| ------ | --------- | --------------- |
| 0      | `#60A5FA` | Azul - UG-01    |
| 1      | `#A78BFA` | Roxo - UG-02    |
| 2      | `#34D399` | Verde - UG-03   |
| 3      | `#FB923C` | Laranja - UG-04 |
| 4      | `#FB7185` | Rosa - UG-05    |

Para alterar as cores de todo o sistema, edite apenas `libs/models/colors.py`.

## Como Executar Localmente

1. Ative o ambiente virtual e instale as dependências:
   ```bash
   source /home/jrmfilho23/projetos/amb/bin/activate
   pip install -r requirements.txt
   ```

2. Configure o arquivo `.env`:
   ```env
   URL_API=https://...
   API_TOKEN=...
   SECRET_KEY=change-me
   ```

3. Verifique a configuração em `config/usinas_dispositivos.json` com os IPs e registros Modbus das usinas.

4. Execute a aplicação:
   ```bash
   python dashboard.py
   ```
   O servidor iniciará em `http://0.0.0.0:5000` e abrirá automaticamente uma janela Chrome dedicada, se disponível.

## Deploy

O deploy é contínuo e automático via GitHub no **Railway**. O arquivo `Procfile` se encarrega de executar a inicialização via gunicorn/python (`python dashboard.py`).

---
**Créditos**: Desenvolvido por EngeGOM.
