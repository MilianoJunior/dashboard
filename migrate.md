# Migração Streamlit -> Flask

## Objetivo

Migrar o dashboard atual de `Streamlit` para `Flask`, mantendo a paridade funcional do painel operacional e reduzindo o acoplamento da camada de interface com a camada de consulta de dados.

O ponto de partida da nova aplicação já existe em `dashboard.py`.

## Estado Atual da Migração

### O que já está pronto no Flask

- Existe uma aplicação Flask funcional em `dashboard.py`.
- A rota `/` já renderiza o dashboard principal via Jinja.
- A base visual já foi quebrada em templates parciais:
  - `libs/views/componentes/base.html`
  - `libs/views/componentes/dashboard.html`
  - `libs/views/componentes/gauge_grid.html`
  - `libs/views/componentes/generation_chart.html`
  - `libs/views/componentes/reservoir_chart.html`
- O gráfico de geração já está integrado com dados reais da API.
- O gráfico de nível do reservatório já está integrado com dados reais da API.
- Os filtros por período e intervalo de datas já funcionam no dashboard Flask via query string (`GET`).
- A camada de consulta e normalização foi reaproveitada de forma correta em `libs/controllers/consultas.py`, sem depender de `streamlit`.
- A configuração de `Flask` já está declarada no projeto em `requirements.txt`.

### O que já foi migrado de forma parcial

- Estrutura visual do dashboard principal.
- Header e navegação base.
- Grid de gauges.
- Seção de geração acumulada.
- Seção de nível dos reservatórios.

### O que ainda está mockado ou incompleto no Flask

- Os gauges ainda usam dados mockados em `get_dashboard_data()`.
- A usina atual ainda está fixa em `dashboard.py`:
  - hoje a aplicação usa apenas a primeira usina da lista.
- O header e o bottom nav ainda são placeholders visuais.
- Não existe autenticação real no Flask.
- Não existe sessão por usina no Flask.
- Não existe troca de usina no Flask.
- Não existem rotas auxiliares para exportação de dados.
- Não existe ainda a parte de análise personalizada.
- Não existe ainda a calculadora de receita com cards mensais.

## O que continua existindo apenas no Streamlit

As funcionalidades abaixo ainda vivem no app antigo e precisam ser migradas:

- Login por usina com senha específica.
- Persistência de sessão por usina.
- Carregamento da configuração de usinas via `config_controller.py`.
- Seleção dinâmica da usina ativa.
- Calculadora de receita.
- Cards mensais de geração.
- Gráfico exploratório de variáveis selecionadas.
- Consulta de grupos e variáveis da API.
- Exportação CSV/Excel dos dataframes.
- Fluxo de logout.
- Controle de carregamento e estados de sessão via `st.session_state`.

## Pontos Críticos Identificados

### 1. A aplicação nova ainda não está pronta para múltiplas usinas

Hoje o Flask está preso a uma usina hardcoded. Enquanto isso não for resolvido, a migração não substitui o comportamento real do sistema.

### 2. Os gauges ainda não representam dados reais

A parte visual existe, mas a origem dos dados de status, percentual e potência ainda não foi ligada a nenhuma fonte real.

### 3. O deploy ainda aponta para o app Streamlit

O `Procfile` atual ainda executa:

```text
web: streamlit run main.py --server.port $PORT --server.address 0.0.0.0
```

Ou seja: mesmo com `dashboard.py` pronto, o deploy ainda não sobe o Flask.

### 4. A autenticação ainda é um bloqueio funcional

Sem login, sem sessão e sem usina corrente, a aplicação Flask ainda não substitui o fluxo operacional atual.

### 5. Ainda não existe camada de rotas separada

Tudo ainda está concentrado em `dashboard.py`. Para crescer com login, análise personalizada, exportação e múltiplas páginas, vai ficar melhor separar rotas, serviços e templates por responsabilidade.

## Próximos Passos Prioritários

## Fase 1 - Destravar a base funcional do Flask

1. Implementar seleção de usina no Flask.
   - Remover a usina hardcoded.
   - Carregar as usinas a partir de `config/usuarios_usinas.yaml`.
   - Definir a usina corrente por sessão.

2. Implementar autenticação e sessão.
   - Criar rota `/login`.
   - Criar rota `/logout`.
   - Validar senha por usina.
   - Persistir sessão no Flask.
   - Decidir se o comportamento de "lembrar senha por usina" será mantido igual ao Streamlit ou simplificado.

3. Estruturar melhor a aplicação Flask.
   - Separar rotas do dashboard.
   - Separar autenticação.
   - Separar montagem dos dados do dashboard.
   - Evitar que `dashboard.py` vire um arquivo monolítico.

## Fase 2 - Fechar paridade do dashboard principal

4. Substituir os gauges mockados por dados reais.
   - Confirmar a fonte dos dados.
   - Definir regra de status (`Ativa`, `Atenção`, `Crítico`).
   - Definir origem de `%` e `MW`.

5. Migrar a calculadora de receita.
   - Reaproveitar a lógica dos cards mensais do app atual.
   - Renderizar os cards no Flask.
   - Manter o cálculo `MWh x valor do MWh x participação`.

6. Migrar exportação de dados.
   - CSV para geração.
   - Excel para geração.
   - CSV/Excel para nível.
   - Depois repetir para análise personalizada.

## Fase 3 - Migrar funcionalidades avançadas

7. Migrar a análise personalizada.
   - Buscar grupos via `/grupos/{usina}`.
   - Exibir variáveis por grupo.
   - Consultar séries em `/sensor-usina`.
   - Renderizar gráfico multi-séries no Flask.
   - Adicionar exportação.

8. Melhorar tratamento de erro e estados vazios.
   - Falha de API.
   - Período sem dados.
   - Usina sem variáveis.
   - Sessão expirada.

9. Adicionar cache e otimização.
   - Evitar consultas repetidas para o mesmo filtro.
   - Avaliar cache por usina/período.
   - Reaproveitar normalizações já desacopladas.

## Fase 4 - Fechar operação e deploy

10. Ajustar o deploy para Flask.
    - Adicionar servidor WSGI de produção.
    - Alterar `Procfile`.
    - Validar execução no Railway.

11. Criar testes da nova camada Flask.
    - Testes de rota.
    - Testes de autenticação.
    - Testes de montagem do contexto do template.
    - Testes das consultas desacopladas.

12. Fazer limpeza final da migração.
    - Remover dependência residual do Streamlit do fluxo principal.
    - Deixar o app antigo apenas como referência temporária.
    - Eliminar templates de protótipo não utilizados, se ainda fizer sentido.

## Ordem Recomendada de Implementação

Se a ideia é começar a codificar agora, a ordem mais segura é:

1. Login + sessão + seleção de usina.
2. Remoção da usina hardcoded.
3. Organização mínima das rotas e da montagem de contexto.
4. Gauges com dados reais.
5. Calculadora de receita + cards mensais.
6. Exportação do dashboard principal.
7. Análise personalizada.
8. Deploy Flask no Railway.
9. Testes.

## Critério de Migração Concluída

Vamos considerar a migração realmente concluída quando:

- o usuário conseguir acessar via login no Flask;
- a usina for selecionada dinamicamente;
- geração e nível estiverem operando com dados reais;
- gauges estiverem em dados reais;
- cards/calculadora estiverem migrados;
- análise personalizada estiver migrada;
- exportações estiverem disponíveis;
- o deploy do Railway estiver apontando para o Flask;
- o fluxo principal não depender mais do Streamlit.

## Observações Úteis

- `libs/controllers/consultas.py` é hoje o melhor ponto de reaproveitamento da migração.
- `dashboard.py` já prova que a abordagem Flask funciona com a API atual.
- `libs/views/home.html` parece ser um protótipo estático antigo e não o template principal em uso.
- O principal gargalo funcional neste momento não é layout, e sim sessão, usina corrente e remoção dos mocks.
