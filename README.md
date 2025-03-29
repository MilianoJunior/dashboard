# Dashboard EngeGOM

## Início do Projeto
- Definir os objetivos do dashboard e identificar as usinas (usuários)
- Estabelecer a tabela de usuário da usina com os campos:
  - `id`
  - `usuario`
  - `senha`
  - `ip_usina`
  - `table_usina`
  - `qtd_access`
  - `date_created`

## Configuração do Ambiente
- Criar um ambiente virtual Python
- Instalar as dependências necessárias:
  - `streamlit`
  - `mysql-connector-python`
  - `python-dotenv`
  - `bcrypt`

## Estrutura do Projeto
Organizar as pastas e arquivos essenciais:
- Arquivo principal (`main.py`)
- Arquivo de variáveis sensíveis (`.env`)
- Pasta `.streamlit` contendo o arquivo `config.toml` para configurar o tema dark
- Pasta `libs` com módulos:
  - `auth.py` (para autenticação e hash)
  - `db.py` (para conexão e gerenciamento do banco de dados)

## Configuração de Segurança e Interface
- No arquivo `.env`:
  - Definir as credenciais do banco de autenticação
  - Configurar uma `SECRET_KEY`
- Configurar o `.streamlit/config.toml` para utilizar o tema dark
- Assegurar que o `.env` esteja protegido (via `.gitignore`)

## Sistema de Login e Autenticação
- Criar a tabela de usuários com os campos estipulados
- Implementar autenticação utilizando:
  - Verificação de senha com bcrypt
  - Gerenciamento de sessão via `st.session_state`

## Conexão Dinâmica
- Associar cada usuário ao seu banco de dados específico
- Persistir configurações na sessão do usuário:
  - host
  - usuário
  - senha
  - nome do banco

## Dashboard Personalizado
- Carregar dados do banco associado ao usuário logado
- Exibir informações através de componentes interativos:
  - Tabelas
  - Gráficos
- Adaptar interface conforme a usina acessada

## Testes e Integração
Métodos para testar cada módulo:
- Teste de conexão com banco de dados
- Teste de autenticação
- Sanitização de entradas do usuário
- Tratamento de erros com mensagens claras
- Integração sequencial das partes

## Execução
```bash
streamlit run main.py
```

## Comandos SQL
Definir comandos SQL para inserção na tabela de usuários com valores apropriados para:
- Testes iniciais
- Funcionamento do sistema

## Funcionalidades-Chave
- Autenticação segura com hash de senhas
- Isolamento de dados por usuário
- Interface responsiva e customizada (tema dark)
- Estrutura modular com testes sequenciais