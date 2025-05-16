# Dashboard EngeGOM

# Análise e Organização do Dashboard EngeGOM

## Estrutura Atual

O projeto atual é uma aplicação dashboard baseada em Streamlit para usinas hidrelétricas (CGH/PCH) com os seguintes componentes:

1. **Aplicação Principal (`main.py`)**
   - Gerencia layout da UI, autenticação de usuário e fluxo geral da aplicação
   - Coordena carregamento de dados e visualização

2. **Módulos de Biblioteca**
   - `componentes.py`: Componentes de UI como cards, gráficos e calculadoras
   - `db.py`: Funções de conexão e recuperação de dados do banco de dados
   - `menu.py`: Arquivo vazio/placeholder (possível funcionalidade futura)

3. **Diretórios de Suporte**
   - `assets/`: Contém logos e outros recursos estáticos
   - `config/`: Contém arquivos de configuração (ex: `usuarios_usinas.yaml`)
   - `testes/`: Scripts de teste para funcionalidade de banco de dados

## Problemas e Recomendações

### 1. Organização do Código

**Problemas:**
- Funções não estão adequadamente separadas por responsabilidade
- Funcionalidade duplicada entre arquivos
- Lógica de apresentação e manipulação de dados misturadas
- Estrutura de módulos incompleta (`logger.py` existe mas está vazio)

**Recomendações:**
- Refatorar para um padrão claro Modelo-Visão-Controlador (MVC):
  ```
  libs/
  ├── models/         # Modelos de dados e interações com banco de dados
  │   ├── db.py       # Funções de banco de dados de baixo nível
  │   └── data.py     # Transformação de dados e lógica de negócios
  ├── views/          # Componentes de UI
  │   ├── components.py  # Elementos de UI reutilizáveis
  │   ├── charts.py      # Lógica de geração de gráficos
  │   └── pages.py       # Layouts de página completos
  └── controllers/    # Lógica da aplicação
      ├── auth.py     # Autenticação
      ├── session.py  # Gerenciamento de estado da sessão
      └── config.py   # Manipulação de configuração
  ```

### 2. Autenticação

**Problemas:**
- Credenciais codificadas diretamente (`admin/admin`)
- Segurança mínima
- Gerenciamento de sessão misturado com lógica da aplicação

**Recomendações:**
- Criar módulo de autenticação dedicado
- Implementar hash de senha adequado
- Usar `st.experimental_get_query_params()` do Streamlit para gerenciamento de sessão mais seguro

### 3. Interações com Banco de Dados

**Problemas:**
- Logging excessivo em funções de banco de dados
- Tratamento de erros inconsistente
- Queries SQL diretamente nas funções
- Reconecta ao banco de dados frequentemente

**Recomendações:**
- Implementar pooling de conexão
- Criar uma classe de banco de dados para encapsular funcionalidade
- Separar definição de query da execução
- Padronizar tratamento de erros

### 4. Componentes de Frontend

**Problemas:**
- CSS inline misturado com lógica de componentes
- Nenhum sistema de estilização consistente
- Funções com múltiplas responsabilidades

**Recomendações:**
- Separar estilização em arquivos CSS dedicados ou um módulo de tema
- Dividir componentes de UI complexos em peças menores e reutilizáveis
- Implementar validação de parâmetros adequada

### 5. Processamento de Dados

**Problemas:**
- Lógica de negócios misturada com apresentação
- Múltiplas transformações de dados em diferentes funções
- Dados frequentemente reprocessados desnecessariamente

**Recomendações:**
- Criar modelos de dados claros
- Implementar cache para operações caras
- Separar aquisição de dados da transformação

### 6. Configuração

**Problemas:**
- Configuração carregada em múltiplos lugares
- Sem validação de valores de configuração
- Tratamento de erros limitado para configuração ausente

**Recomendações:**
- Criar um serviço de configuração dedicado
- Implementar validação para valores de configuração
- Usar variáveis de ambiente para informações sensíveis

## Plano de Implementação

1. **Fase 1: Refatoração**
   - Reorganizar código sem alterar funcionalidade
   - Estabelecer estrutura de diretório adequada
   - Implementar logging básico

2. **Fase 2: Melhorias**
   - Aprimorar recursos de segurança
   - Melhorar tratamento de erros
   - Implementar estratégias de cache

3. **Fase 3: Extensões**
   - Adicionar testes unitários
   - Implementar integração contínua
   - Criar documentação
   - Adicionar novos recursos

## Melhorias Específicas de Código

1. **Criar uma classe `Database` adequada:**
```python
class Database:
    def __init__(self, config):
        self.config = config
        self.connection = None
        
    def connect(self):
        # Lógica de conexão
        
    def execute_query(self, query, params=None):
        # Execução de query
        
    def fetch_data(self, table, columns=None, conditions=None, date_range=None):
        # Busca de dados com parametrização adequada
```

2. **Implementar uma classe `ChartBuilder`:**
```python
class ChartBuilder:
    @staticmethod
    def create_level_chart(data, columns, title=None):
        # Lógica de criação de gráfico
        
    @staticmethod
    def create_energy_chart(data, period="monthly"):
        # Lógica de criação de gráfico
```

3. **Criar uma classe `AuthManager`:**
```python
class AuthManager:
    @staticmethod
    def login(username, password, usina):
        # Lógica de login
        
    @staticmethod
    def logout():
        # Lógica de logout
```

Esta abordagem tornará o código mais manutenível, testável e extensível para funcionalidades futuras.

## Como Executar

1. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
2. Configure as variáveis de ambiente (.env) e o arquivo `config/usuarios_usinas.yaml`.
3. Execute o dashboard:
   ```
   streamlit run main.py
   ```

---

## Análise Crítica

A estrutura atual funciona para um MVP, mas não escala bem para múltiplas usinas, novos recursos ou equipe maior. A ausência de separação de responsabilidades dificulta a manutenção e a evolução do sistema. Recomenda-se fortemente a refatoração para um padrão MVC, centralização de configuração, uso de variáveis de ambiente para dados sensíveis e maior modularização dos componentes de UI e lógica de dados.

**Próximos Passos Sugeridos:**
- Refatorar para MVC, começando pela separação de lógica de dados e UI.
- Implementar autenticação segura.
- Criar testes unitários para funções críticas.
- Documentar endpoints, fluxos e dependências.

---

## Créditos

Desenvolvido por EngeGOM.