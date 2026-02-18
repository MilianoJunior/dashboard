# Instruções locais para o agente (AGENTS.md)

## 🚫 GIT — PROIBIÇÃO ABSOLUTA

**O agente NUNCA executa os seguintes comandos, sem exceção, mesmo que o usuário peça:**

```
git add
git commit
git push
git merge
git rebase
git reset
git checkout (troca de branch)
git stash
```

- **Commits, pushes e qualquer operação que altere o histórico são responsabilidade exclusiva do usuário.**
- O agente pode apenas sugerir o comando para o usuário copiar e executar manualmente.
- O agente pode usar `git status`, `git log`, `git diff` apenas para leitura e diagnóstico.
- **Motivo:** este repositório está vinculado ao Railway (deploy automático a cada push). Um push indevido vai direto para produção.

---

## 🚫 config/usinas.json — ARQUIVO SAGRADO

- **NUNCA modificar `config/usinas.json` sem confirmação explícita do usuário.**
- Cada usina tem nomes de colunas únicos, definidos pelo CLP/fabricante de cada instalação. Não existe "padronização" possível sem validar contra o banco real.
- O que parece um erro de naming pode ser o nome exato da coluna no banco. Nunca assumir.
- Se o agente identificar uma possível inconsistência, deve **apontar e perguntar** — nunca corrigir por conta própria.
- **Motivo:** uma coluna errada nesse arquivo gera query inválida em produção silenciosamente.

---

## 💬 PROTOCOLO: CONSULTAR ANTES DE AGIR

Para qualquer mudança que afete:

- `config/usinas.json`
- `libs/calculos.py` (lógica de energia por usina)
- `libs/processador_telemetria.py` (filtros e resample)
- Qualquer lógica que trate usinas de forma diferenciada

O agente deve **primeiro apresentar o que pretende mudar e por quê**, aguardar confirmação, e só então executar.

Formato da consulta:

```
⚠️ ANTES DE MODIFICAR
Arquivo: <arquivo>
Mudança: <o que vai mudar>
Motivo: <por que parece necessário>
Risco: <o que pode quebrar>
Pergunta: Confirma?
```

**Exceção:** mudanças em `main.py` (rotas, validações) e `libs/db.py` (conexão) podem ser feitas diretamente, pois não dependem de nuances por usina.

---

## ⚠️ REGRAS CRÍTICAS — NUNCA VIOLAR

1. **NUNCA instalar pacotes sem ativar o venv primeiro.**
   - Ambiente virtual obrigatório: `/home/jrmfilho23/projetos/amb/`
   - Qualquer `pip install` deve ser precedido de `source /home/jrmfilho23/projetos/amb/bin/activate`

2. **NUNCA rodar `pip install` diretamente no Python global do sistema.**
   - Sempre verificar se o pacote já existe no venv antes de instalar:
     `source /home/jrmfilho23/projetos/amb/bin/activate && python -c "import <pacote>"`

3. **NUNCA propor comandos destrutivos sem confirmação explícita do usuário.**
   - Exemplos: `DROP TABLE`, `DELETE FROM`, `rm -rf`, sobrescrever arquivos de config.

4. **NUNCA modificar arquivos de configuração sensíveis sem backup:**
   - `.env`, `config/usinas.json`, arquivos de banco de dados.

---

## Ambiente Python obrigatório

- Sempre executar comandos Python e testes usando o ambiente virtual:
  - `source /home/jrmfilho23/projetos/amb/bin/activate`
- Ao rodar qualquer teste/comando, preferir no mesmo comando:
  - `source /home/jrmfilho23/projetos/amb/bin/activate && <comando>`

## Padrões de código obrigatórios

- Todo arquivo Python começa com o bloco `# FLUXO DO MÓDULO`
- Funções pequenas e focadas (princípio da responsabilidade única)
- Tratamento de erros centralizado via decorators quando possível
- Nomes de variáveis e funções adaptados ao domínio de hidrelétricas
