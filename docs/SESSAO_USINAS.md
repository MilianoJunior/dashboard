# Sistema de Sessão por Usina

## Visão Geral

Sistema de autenticação persistente que armazena credenciais por usina usando cookies do navegador.

**Validade**: 10 dias  
**Escopo**: Independente por usina (múltiplas sessões simultâneas)

---

## Fluxo de Autenticação

```
1. Usuário acessa sistema
   ↓
2. Sistema verifica cookies existentes
   ↓
3. Se cookie da usina existe → auto-preenche senha
   ↓
4. Usuário confirma login
   ↓
5. Sistema valida credenciais
   ↓
6. Se válido → cria/atualiza cookie com validade de 10 dias
   ↓
7. Sessão ativa no st.session_state
```

---

## Implementação Técnica

### Armazenamento

**Biblioteca**: `extra_streamlit_components.CookieManager`

**Estrutura do Cookie**:
```python
{
    "CGH-FAE": "fae102",
    "CGH-PICADAS-ALTAS": "picadas104",
    "PCH-PEDRAS": "pedras25",
    # ... outras usinas
}
```

Cada usina é uma chave separada no cookie manager.

### Código Principal

**Localização**: `libs/views/componentes.py`

**Funções**:

1. `get_cookie_manager()` → Inicializa gerenciador
2. `login_ui()` → Interface de login com auto-fill

**Trecho Crítico**:
```python
# Auto-fill da senha se cookie existe
senha_padrao = todos_cookies.get(usina_nome, "") if usina_nome else ""
senha = st.text_input('Senha', type='password', value=senha_padrao)

# Após autenticação bem-sucedida
if autenticado:
    expiracao = datetime.now() + timedelta(days=10)
    cookie_manager.set(usina_nome, senha, expires_at=expiracao)
```

---

## Segurança

### ⚠️ Considerações

1. **Senha em texto plano no cookie** → Risco se dispositivo comprometido
2. **Sem criptografia adicional** → Navegador gerencia segurança básica
3. **Validade longa (10 dias)** → Conveniência vs. segurança

### ✅ Mitigações Aplicadas

- Cookies são `httpOnly` por padrão (não acessíveis via JS)
- Expiração automática após 10 dias
- Cada usina tem credencial isolada
- Logout limpa `st.session_state` (não remove cookies)

### 🔒 Melhorias Futuras (Opcional)

```python
# Opção 1: Hash da senha no cookie
import hashlib
senha_hash = hashlib.sha256(senha.encode()).hexdigest()
cookie_manager.set(usina_nome, senha_hash, expires_at=expiracao)

# Opção 2: Token JWT
import jwt
token = jwt.encode({"usina": usina_nome, "exp": expiracao}, SECRET_KEY)
cookie_manager.set("auth_token", token, expires_at=expiracao)
```

---

## Comportamento por Cenário

| Cenário | Comportamento |
|---------|---------------|
| Primeiro acesso | Campo senha vazio, usuário digita |
| Acesso dentro de 10 dias | Senha auto-preenchida |
| Após 10 dias | Cookie expira, campo vazio |
| Troca de usina | Cada usina tem seu próprio cookie |
| Logout | Session limpa, cookies permanecem |
| Senha errada salva | Usuário precisa apagar e redigitar |

---

## Manutenção

### Alterar Validade

**Arquivo**: `libs/views/componentes.py`  
**Linha**: ~425

```python
# Alterar de 10 para X dias
expiracao = datetime.now() + timedelta(days=X)
```

### Limpar Cookies Manualmente

```python
# Adicionar função de limpeza (se necessário)
def limpar_cookies():
    cookie_manager = get_cookie_manager()
    for usina in st.session_state.get('usinas', {}).keys():
        cookie_manager.delete(usina)
```

---

## Dependências

```bash
pip install extra-streamlit-components
```

**Versão testada**: `0.1.56`

---

## Logs e Monitoramento

O sistema registra acessos em:

**Arquivo**: `libs/controllers/auth.py`  
**Função**: `register_user()`

```python
# Incrementa contador de acessos
config['usinas'][selected_usina_nome]['acesso'] += 1

# Salva em config/usinas_cont.yaml
```

---

## Troubleshooting

### Problema: Senha não auto-preenche

**Causa**: Cookie expirou ou foi deletado  
**Solução**: Redigitar senha (novo cookie será criado)

### Problema: Senha errada salva no cookie

**Causa**: Usuário digitou errado e cookie foi salvo  
**Solução**: Limpar cookies do navegador ou aguardar expiração

### Problema: Múltiplas usinas com mesma senha

**Causa**: Senhas hardcoded em `auth.py`  
**Solução**: Cada usina tem senha única no dicionário `senhas{}`

---

## Referências

- [extra-streamlit-components](https://github.com/Mohamed-512/Extra-Streamlit-Components)
- [Streamlit Session State](https://docs.streamlit.io/library/api-reference/session-state)
