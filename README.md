# Dashboard EngeGOM

Dashboard web para monitoramento operacional de usinas hidrelétricas (CGH/PCH), desenvolvido pela EngeGOM.

## Visao Geral

Aplicacao Flask + Flask-SocketIO que exibe em tempo real e historicamente:

- **Gauges de potencia** de cada Unidade Geradora (UG), com status e percentual de carga
- **Nivel de montante** (nivel d'agua a montante da barragem)
- **Graficos de producao de energia** (horaria, diaria e mensal)
- **Graficos de nivel** com linha de vertimento

Os dados historicos vem de uma API REST externa (`/producao-acumulada`, `/grupo-usina`, `/sensor-usina`). Os dados em tempo real sao lidos via API Modbus/CLP e enviados ao frontend por WebSocket.

## Usinas Suportadas

| Codigo | Tipo |
|---|---|
| PCH-PIRA | PCH |
| PCH-PEDRAS | PCH |
| CGH-APARECIDA | CGH |
| CGH-PICADAS-ALTAS | CGH |
| CGH-FAE | CGH |
| CGH-HOPPEN | CGH |

## Estrutura do Projeto

```
dashboard.py                  # Entrypoint Flask + SocketIO
libs/
  routes/routes.py            # Rotas HTTP (/, /health)
  controllers/
    dashboard_controller.py   # Logica de montagem dos dados do dashboard
    consultas.py              # Controller de consultas auxiliares
  models/
    api_model.py              # Chamadas HTTP para API externa (producao, nivel, sensor)
    consultas.py              # Consulta e normalizacao de dados (producao, nivel)
    config_model.py           # Modelo de configuracao
    gauge_rt.py               # Logica de gauges e status das UGs
    utils.py                  # Filtros de template e utilitarios
  views/
    componentes/              # Templates HTML (dashboard, componentes)
    servicos/
      connect.py              # WebSocket: leitura RT via Modbus e emissao periodica
      read_rt.py              # Leitura de dados em tempo real
  utils/
    decorators.py             # Decorador de desempenho
config/
  usinas_dispositivos.json    # Configuracao de dispositivos/registros Modbus por usina
  usuarios_usinas.yaml        # Mapeamento usuarios x usinas
  usinas_cont.yaml            # Configuracao de contabilizacao
assets/                       # Logos e recursos estaticos
tests/                        # Testes automatizados
docs/                         # Codigo legado (Streamlit) e documentacao
```

## Arquitetura

```
Browser  <--WebSocket-->  Flask-SocketIO  <--HTTP/Modbus-->  API CLP
Browser  <--HTTP GET-->   Flask Routes    <--HTTP POST-->    API REST externa
```

1. O usuario acessa `/` e recebe o dashboard renderizado com dados historicos
2. O SocketIO inicia emissao periodica (~15-20s) lendo dados RT de cada UG via API Modbus
3. O frontend atualiza os gauges e resumo em tempo real sem reload

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
   O servidor sobe em `http://0.0.0.0:5000`.

## Deploy

Deploy automatico via GitHub no **Railway**. O `Procfile` executa `python dashboard.py`.

## Creditos

Desenvolvido por EngeGOM.
