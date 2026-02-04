# Comportamento do CookieManager - Streamlit

## Problema Identificado

O `extra-streamlit-components.CookieManager` tem um **comportamento assíncrono** que causa confusão:

### ❌ O que NÃO funciona

```python
# Salvar cookie
cookie_manager.set('usina', 'senha123', expires_at=expiracao)

# Tentar ler imediatamente
cookies = cookie_manager.get_all()
print(cookies)  # ❌ Cookie NÃO aparece aqui!
```

### ✅ O que funciona

```python
# 1. Salvar cookie
cookie_manager.set('usina', 'senha123', expires_at=expiracao)

# 2. Recarregar página (F5 ou st.rerun())

# 3. Agora o cookie está disponível
cookies = cookie_manager.get_all()
print(cookies)  # ✅ Cookie aparece aqui!
```

---

## Por que isso acontece?

O `CookieManager` funciona através de **comunicação JavaScript ↔ Python**:

1. **Python → JavaScript**: `cookie_manager.set()` envia comando para o navegador
2. **JavaScript**: Navegador salva o cookie
3. **JavaScript → Python**: Cookie só volta para Python na **próxima requisição HTTP**

---

## Fluxo Correto no Sistema

### Login (Primeira vez)

```
1. Usuário digita senha
   ↓
2. Sistema valida credenciais
   ↓
3. cookie_manager.set('CGH-FAE', 'fae102', expires_at=...)
   ↓
4. st.session_state['logado'] = True
   ↓
5. st.rerun() → Redireciona para dashboard
   ↓
6. Cookie salvo no navegador (mas ainda não disponível em Python)
```

### Próximo Acesso (Mesmo dia)

```
1. Usuário abre sistema
   ↓
2. cookie_manager.get_all() → Lê cookies do navegador
   ↓
3. Senha auto-preenchida ✅
   ↓
4. Usuário clica "Entrar"
```

---

## Implicações Práticas

### ✅ O que funciona

- **Auto-fill na próxima sessão**: Cookie salvo hoje aparece amanhã
- **Múltiplas usinas**: Cada usina tem cookie independente
- **Expiração**: Cookie expira automaticamente após 10 dias

### ⚠️ Limitações

- **Não funciona no mesmo carregamento**: Cookie salvo agora só aparece após F5
- **Não funciona para validação imediata**: Não dá para verificar se salvou sem recarregar
- **Dependente do navegador**: Limpar cookies do navegador apaga tudo

---

## Solução Implementada

### Código Final

```python
def login_ui():
    cookie_manager = get_cookie_manager()
    todos_cookies = cookie_manager.get_all()  # Lê cookies salvos anteriormente
    
    # Selectbox com callback
    def on_usina_change():
        usina_atual = st.session_state.get('usina_login')
        senha_cookie = todos_cookies.get(usina_atual, "")
        st.session_state['senha_login'] = senha_cookie  # Atualiza senha
    
    usina_nome = st.selectbox('Selecione a usina', usinas, on_change=on_usina_change)
    
    # Inicializar senha
    if 'senha_login' not in st.session_state:
        st.session_state['senha_login'] = todos_cookies.get(usina_nome, "")
    
    senha = st.text_input('Senha', type='password', key='senha_login')
    
    if st.button("Entrar"):
        if autenticado:
            # Salvar cookie (disponível no próximo acesso)
            cookie_manager.set(usina_nome, senha, expires_at=expiracao)
            
            # Limpar keys para evitar conflitos
            del st.session_state['senha_login']
            del st.session_state['usina_login']
            
            st.session_state['logado'] = True
            st.rerun()  # Redireciona para dashboard
```

---

## Testes Realizados

### Teste 1: Login CGH-FAE
```
✅ Login bem-sucedido
✅ Redirecionou para dashboard
✅ Cookie salvo no navegador
❌ Cookie NÃO aparece em get_all() imediatamente
✅ Cookie APARECE após F5
```

### Teste 2: Login CGH-APARECIDA
```
✅ Login bem-sucedido
✅ Redirecionou para dashboard
✅ Cookie salvo no navegador
✅ Cookie APARECE após F5
```

### Teste 3: Trocar entre usinas
```
✅ Selecionar CGH-FAE → Senha auto-preenchida
✅ Selecionar CGH-APARECIDA → Senha auto-preenchida
✅ Callback funcionando corretamente
```

---

## Alternativas (Não Implementadas)

### Opção 1: Usar st.session_state apenas

**Prós**: Disponível imediatamente  
**Contras**: Perde ao fechar navegador (não persiste)

### Opção 2: Salvar em arquivo local

**Prós**: Controle total  
**Contras**: Segurança (senha em texto plano no disco)

### Opção 3: Usar localStorage via JavaScript

**Prós**: Mais controle  
**Contras**: Complexidade (precisa de componente customizado)

---

## Conclusão

O comportamento atual é **correto e esperado** para o `CookieManager`.

**Fluxo normal**:
1. Login → Cookie salvo
2. Recarregar página → Cookie disponível
3. Auto-fill funciona ✅

**Não é bug**, é característica da arquitetura Streamlit + JavaScript.
