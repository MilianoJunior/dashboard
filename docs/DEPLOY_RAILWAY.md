# Checklist de Deploy - Railway

## ✅ Pré-Deploy

### 1. Dependências
- [x] `requirements.txt` atualizado
- [x] Removido `datetime` (built-in do Python)
- [x] Todas as libs usadas estão listadas

### 2. Variáveis de Ambiente
Certifique-se que o Railway tem as seguintes variáveis configuradas:

```env
# Banco de Dados
DB_HOST=seu_host_mysql
DB_USER=seu_usuario
DB_PASSWORD=sua_senha
DB_NAME=nome_do_banco

# Streamlit (opcional)
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
```

### 3. Arquivos de Configuração
- [x] `.streamlit/config.toml` (se existir)
- [x] `config/usinas_dispositivos.json`
- [x] `config/usinas_cont.yaml`

---

## 📋 Mudanças Implementadas (Sistema de Sessão)

### Arquivos Modificados
1. `libs/views/componentes.py`
   - Implementado auto-fill de senha via cookies
   - Callback para trocar usina dinamicamente
   - Limpeza de session_state após login

2. `libs/controllers/auth.py`
   - Mantido sistema de autenticação existente
   - Registro de acessos funcionando

### Arquivos Criados (Documentação)
1. `docs/SESSAO_USINAS.md` - Documentação técnica
2. `docs/GUIA_USUARIO_SESSAO.md` - Guia para cliente
3. `docs/COMPORTAMENTO_COOKIES.md` - Explicação do CookieManager
4. `tests/test_sessao_usinas.py` - Testes (não afeta produção)

---

## 🚀 Deploy no Railway

### Passo 1: Commit e Push
```bash
git add .
git commit -m "feat: implementado sistema de sessão por usina com cookies (10 dias)"
git push origin main
```

### Passo 2: Railway Auto-Deploy
O Railway detectará automaticamente:
- ✅ `requirements.txt` → Instalará dependências
- ✅ `main.py` → Executará `streamlit run main.py`
- ✅ Porta 8501 → Exposta automaticamente

### Passo 3: Verificar Logs
Após deploy, verifique:
```
✓ Build successful
✓ Dependencies installed
✓ Streamlit running on port 8501
✓ Database connection OK
```

---

## ⚠️ Pontos de Atenção

### 1. Cookies no Railway
- ✅ Funcionam normalmente (HTTP/HTTPS)
- ✅ Cada cliente terá seus próprios cookies
- ⚠️ Se Railway reiniciar, cookies do navegador **permanecem**

### 2. Session State
- ⚠️ `st.session_state` é **por sessão do navegador**
- ⚠️ Se Railway reiniciar, usuários precisam fazer login novamente
- ✅ Mas a **senha estará preenchida** (cookie)

### 3. Banco de Dados
- ✅ Conexão via variáveis de ambiente
- ✅ `mysql-connector-python` instalado
- ⚠️ Verificar se Railway tem acesso ao MySQL

---

## 🧪 Testes Pós-Deploy

### Teste 1: Login Inicial
1. Acessar URL do Railway
2. Selecionar usina
3. Digitar senha
4. Clicar "Entrar"
5. **Esperado**: Redireciona para dashboard ✅

### Teste 2: Auto-Fill
1. Fazer logout
2. Recarregar página (F5)
3. Selecionar mesma usina
4. **Esperado**: Senha preenchida automaticamente ✅

### Teste 3: Múltiplas Usinas
1. Fazer login em CGH-FAE
2. Fazer logout
3. Fazer login em CGH-APARECIDA
4. Fazer logout
5. Recarregar página
6. **Esperado**: Ambas têm senha salva ✅

### Teste 4: Expiração
1. Aguardar 10 dias (ou ajustar para 1 minuto para teste)
2. Recarregar página
3. **Esperado**: Cookie expirou, campo vazio ✅

---

## 🔧 Troubleshooting

### Problema: "Module not found"
**Solução**: Verificar `requirements.txt` e fazer novo deploy

### Problema: "Database connection failed"
**Solução**: Verificar variáveis de ambiente no Railway

### Problema: Cookies não funcionam
**Solução**: 
- Verificar se Railway usa HTTPS
- Verificar se `extra-streamlit-components` instalou corretamente

### Problema: Redirecionamento não funciona
**Solução**: Verificar logs do Railway, pode ser erro no `st.rerun()`

---

## 📊 Monitoramento

### Logs Importantes
```bash
# No Railway, verificar:
- "função principal: login_ui" → Login carregado
- "accesso: X, data: Y" → Login bem-sucedido
- "função principal: menu_principal" → Dashboard carregado
```

### Métricas
- Acessos por usina: `config/usinas_cont.yaml`
- Erros: Logs do Railway
- Performance: Tempo de carregamento do dashboard

---

## ✅ Checklist Final

Antes de fazer deploy:
- [ ] `requirements.txt` atualizado
- [ ] Variáveis de ambiente configuradas no Railway
- [ ] Código testado localmente
- [ ] Documentação atualizada
- [ ] Commit com mensagem descritiva
- [ ] Push para GitHub
- [ ] Aguardar auto-deploy do Railway
- [ ] Testar URL de produção
- [ ] Notificar clientes sobre nova funcionalidade

---

## 📞 Suporte

Em caso de problemas no deploy:
1. Verificar logs do Railway
2. Testar localmente com `streamlit run main.py`
3. Verificar se todas as dependências estão instaladas
4. Verificar conexão com banco de dados

**Sistema pronto para deploy!** 🚀
