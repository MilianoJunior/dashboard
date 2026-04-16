# Dashboard EngeGOM

Dashboard web para monitoramento operacional de usinas hidreletricas (CGH/PCH), desenvolvido pela EngeGOM.

## Visao Geral

Aplicacao Flask + Flask-SocketIO que exibe em tempo real e historicamente:

- **Gauges de potencia** de cada Unidade Geradora (UG), com status e percentual de carga
- **Nivel de montante** (nivel d'agua a montante da barragem)
- **Graficos de producao de energia** (horaria, diaria e mensal)
- **Graficos de nivel** com linha de vertimento

Os dados historicos vem de uma API REST externa (`/producao-acumulada`, `/grupo-usina`, `/sensor-usina`). Os dados em tempo real sao lidos via API Modbus/CLP e enviados ao frontend por WebSocket.

## Experiencia de Monitoramento em Tempo Real

O frontend foi projetado para transmitir ao operador a sensacao de "sistema vivo":

- **Live Dot**: ponto verde pulsante ao lado do titulo "Resumo Tempo Real", indicando que o sistema esta ativo
- **Timestamp dinamico**: contador regressivo ao lado do titulo mostrando "Atualizado as HH:MM:SS - ha Xs", atualizado a cada segundo
- **Efeito odometro**: valores numericos (percentual, potencia, nivel montante) rolam suavemente do valor antigo ao novo com interpolacao ease-out cubic (800ms)
- **Transicao suave nos arcos**: as barras dos gauges SVG deslizam via CSS transition ao inves de saltar
- **Sparklines com curvas Bezier**: mini-graficos de area em cada card de UG e no resumo, mostrando a tendencia dos ultimos ~15 minutos (ate 50 pontos)
  - Curvas suaves via conversao Catmull-Rom para Bezier cubico
  - Gradiente de area (cor da UG -> transparente) dando volume visual
  - Leading dot pulsante com glow SVG no ponto atual
  - UGs paradas (0%) recuam visualmente: cor cinza, opacidade reduzida, sem dot
- **Atualizacao in-place**: o DOM nunca e destruido/recriado nas atualizacoes via socket, permitindo que todas as animacoes CSS e JS funcionem

## Usinas Suportadas

| Codigo            | Tipo |
| ----------------- | ---- |
| PCH-PIRA          | PCH  |
| PCH-PEDRAS        | PCH  |
| CGH-APARECIDA     | CGH  |
| CGH-PICADAS-ALTAS | CGH  |
| CGH-FAE           | CGH  |
| CGH-HOPPEN        | CGH  |

O numero de UGs e dinamico por usina (1 a N). A paleta de cores e aplicada ciclicamente via `idx % len(UG_COLORS)`.

## Estrutura do Projeto

```
dashboard.py                  # Entrypoint Flask + SocketIO
libs/
  routes/routes.py            # Rotas HTTP (/, /health)
  controllers/
    dashboard_controller.py   # Logica de montagem dos dados do dashboard
  models/
    api_model.py              # Chamadas HTTP para API externa (producao, nivel, sensor)
    consultas.py              # Consulta e normalizacao de dados (producao, nivel)
    config_model.py           # Modelo de configuracao (YAML)
    gauge_rt.py               # Logica de gauges e status das UGs
    colors.py                 # Paleta centralizada de cores (UG_COLORS, NIVEL_COLORS)
    utils.py                  # Filtros de template e utilitarios
  views/
    componentes/
      base.html               # Layout base (Tailwind, fontes, animacoes CSS)
      dashboard.html           # Skeleton de loading + carga assincrona
      gauge_card.html          # Macro Jinja do card individual de UG
      gauge_grid.html          # Grid de gauges + resumo RT + sparklines + socket JS
      generation_chart.html    # Grafico de producao empilhado
      reservoir_chart.html     # Grafico de nivel do reservatorio
      header.html              # Cabecalho com seletor de usina
      bottom_nav.html          # Navegacao inferior
    servicos/
      connect.py              # WebSocket: leitura RT via Modbus e emissao periodica
  utils/
    decorators.py             # Decorador de desempenho e logging
    auth.py                   # Autenticacao de rotas
config/
  usinas_dispositivos.json    # Configuracao de dispositivos/registros Modbus por usina
  usuarios_usinas.yaml        # Mapeamento usuarios x usinas
  usinas_cont.yaml            # Configuracao de contabilizacao
assets/                       # Logos e recursos estaticos
tests/                        # Testes automatizados
docs/                         # Documentacao e codigo legado
```

## Arquitetura

```
Browser  <--WebSocket-->  Flask-SocketIO  <--HTTP/Modbus-->  API CLP
Browser  <--HTTP GET-->   Flask Routes    <--HTTP POST-->    API REST externa
```

1. O usuario acessa `/` e recebe o skeleton de loading (dashboard.html)
2. O JS do skeleton faz um fetch assincrono para `/api/dashboard` que retorna os dados historicos
3. O SocketIO inicia emissao periodica (~15-20s) lendo dados RT de cada UG via API Modbus
4. O frontend atualiza gauges, sparklines e resumo em tempo real sem reload (update in-place)

## Paleta de Cores

Definida em `libs/models/colors.py` (fonte unica de verdade):

| Indice | Cor       | Uso             |
| ------ | --------- | --------------- |
| 0      | `#60A5FA` | Azul - UG-01    |
| 1      | `#A78BFA` | Roxo - UG-02    |
| 2      | `#34D399` | Verde - UG-03   |
| 3      | `#FB923C` | Laranja - UG-04 |
| 4      | `#FB7185` | Rosa - UG-05    |

Para alterar as cores de todo o sistema, edite apenas `libs/models/colors.py`.

## Como Executar

1. Instale as dependencias:

   ```
   pip install -r requirements.txt
   ```

2. Configure o `.env`:

   ```
   URL_API=https://...
   API_TOKEN=...
   SECRET_KEY=...
   ```

3. Configure `config/usinas_dispositivos.json` com IPs e registros Modbus das usinas.

4. Execute:
   ```
   python dashboard.py
   ```
   O servidor sobe em `http://0.0.0.0:5000` e abre automaticamente uma janela Chrome dedicada.

## Deploy

Deploy automatico via GitHub no **Railway**. O `Procfile` executa `python dashboard.py`.

## Creditos

Desenvolvido por EngeGOM.

# 1. Mata o processo pausado no background deste terminal específico

kill -9 %1

# 2. Força o encerramento de qualquer processo do next rodando no seu usuário

pkill -9 -u $USER -f "next"

# 3. Limpa a pasta de cache onde o arquivo de bloqueio do PID ficou preso

rm -rf .next

Não acho “difícil” no sentido de impossível ou mal encaminhado. Acho que ele está numa fase em que
ficou sensível a acoplamento: Flask renderizando HTML, AJAX recarregando pedaços da tela, SocketIO
atualizando em tempo real, regras de negócio por usina, config de CLP e histórico no banco. Cada
parte isolada é simples; o difícil é garantir que elas não se atravessem.

Os pontos que mais aumentam a complexidade hoje são:

- Estado em tempo real por usina: quando SocketIO usa estado global ou broadcast, uma usina pode
  vazar dados para outra tela.
- Templates com JS embutido: ao trocar seção por AJAX, scripts podem ser executados de novo e
  duplicar listeners.
- Regras de status operacional: os estados booleanos do CLP não são sempre “limpos”, então precisa
  regra de coerência com potência.
- Configuração por usina: cada CLP tem nomes e registradores próprios; não dá para padronizar no
  chute.
- Testes antigos misturados com código atual: a suíte completa falha por módulos legados, o que
  atrapalha confiança.

Mas o projeto tem uma base viável. A arquitetura atual funciona para um dashboard industrial
pequeno/médio, desde que a gente imponha alguns limites: SocketIO sempre com contexto por cliente/
usina, componentes JS com cleanup, regras de negócio centralizadas, e testes focados nos pontos
críticos.

Se fosse meu projeto, eu não reescreveria agora. Eu faria uma estabilização incremental:

1. separar claramente “estado inicial renderizado” de “estado RT via SocketIO”;
2. padronizar contrato dos eventos SocketIO com codigo_usina, timestamp, payload;
3. limpar ou isolar testes legados;
4. criar testes pequenos para regras de status, config e montagem de payload;
5. só depois pensar em autenticação, permissões mais finas ou refatorações maiores.

Então: está ficando complexo, mas não está fora de controle. O importante é não deixar regra
operacional espalhar por template, controller e socket ao mesmo tempo.
