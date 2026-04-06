# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. test_cookie_storage → Valida armazenamento de cookies
# 2. test_cookie_expiration → Testa expiração de 10 dias
# 3. test_multiple_usinas → Verifica isolamento entre usinas
# 4. test_auto_fill → Confirma auto-preenchimento
# -------------------------------------------------------------------

import streamlit as st
from datetime import datetime, timedelta
import extra_streamlit_components as stx

# -------------------------------------------------------------------
# CONFIGURAÇÕES
# -------------------------------------------------------------------
DEBUG = True
USINAS_TESTE = ['CGH-FAE', 'CGH-PICADAS-ALTAS', 'PCH-PEDRAS']
SENHAS_TESTE = {
    'CGH-FAE': 'fae102',
    'CGH-PICADAS-ALTAS': 'picadas104',
    'PCH-PEDRAS': 'pedras25'
}

# -------------------------------------------------------------------
# FUNÇÕES DE TESTE
# -------------------------------------------------------------------

def test_cookie_storage():
    """
    Testa se cookies são armazenados corretamente por usina.
    """
    print("=" * 50)
    print("TESTE 1: Armazenamento de Cookies")
    print("=" * 50)
    
    cookie_manager = stx.CookieManager()
    
    # Armazenar cookies para cada usina
    for usina, senha in SENHAS_TESTE.items():
        expiracao = datetime.now() + timedelta(days=10)
        cookie_manager.set(usina, senha, expires_at=expiracao)
        print(f"✓ Cookie armazenado: {usina}")
    
    # Verificar armazenamento
    todos_cookies = cookie_manager.get_all()
    
    for usina, senha in SENHAS_TESTE.items():
        cookie_value = todos_cookies.get(usina)
        assert cookie_value == senha, f"❌ Falha: {usina} esperava {senha}, obteve {cookie_value}"
        print(f"✓ Cookie validado: {usina} = {senha}")
    
    print("\n✅ TESTE 1 PASSOU\n")


def test_cookie_expiration():
    """
    Valida que a expiração está configurada para 10 dias.
    """
    print("=" * 50)
    print("TESTE 2: Expiração de Cookies")
    print("=" * 50)
    
    cookie_manager = stx.CookieManager()
    
    usina_teste = 'CGH-FAE'
    senha_teste = 'fae102'
    
    # Configurar expiração
    expiracao = datetime.now() + timedelta(days=10)
    cookie_manager.set(usina_teste, senha_teste, expires_at=expiracao)
    
    # Calcular diferença esperada
    dias_restantes = (expiracao - datetime.now()).days
    
    print(f"✓ Cookie configurado com expiração em {dias_restantes} dias")
    assert dias_restantes == 10, f"❌ Falha: Esperava 10 dias, obteve {dias_restantes}"
    
    print("\n✅ TESTE 2 PASSOU\n")


def test_multiple_usinas():
    """
    Verifica isolamento entre cookies de diferentes usinas.
    """
    print("=" * 50)
    print("TESTE 3: Isolamento entre Usinas")
    print("=" * 50)
    
    cookie_manager = stx.CookieManager()
    
    # Armazenar cookies
    for usina, senha in SENHAS_TESTE.items():
        expiracao = datetime.now() + timedelta(days=10)
        cookie_manager.set(usina, senha, expires_at=expiracao)
    
    # Verificar que cada usina tem sua própria senha
    todos_cookies = cookie_manager.get_all()
    
    usinas_encontradas = set(todos_cookies.keys())
    usinas_esperadas = set(SENHAS_TESTE.keys())
    
    assert usinas_encontradas == usinas_esperadas, \
        f"❌ Falha: Esperava {usinas_esperadas}, obteve {usinas_encontradas}"
    
    print(f"✓ {len(usinas_encontradas)} usinas isoladas corretamente")
    
    # Verificar que alterar uma não afeta outras
    cookie_manager.set('CGH-FAE', 'nova_senha_teste', expires_at=datetime.now() + timedelta(days=10))
    todos_cookies = cookie_manager.get_all()
    
    assert todos_cookies['CGH-FAE'] == 'nova_senha_teste', "❌ Falha: Cookie não atualizado"
    assert todos_cookies['PCH-PEDRAS'] == 'pedras25', "❌ Falha: Cookie de outra usina foi afetado"
    
    print("✓ Alteração de uma usina não afeta outras")
    print("\n✅ TESTE 3 PASSOU\n")


def test_auto_fill():
    """
    Simula auto-preenchimento de senha baseado em cookie.
    """
    print("=" * 50)
    print("TESTE 4: Auto-preenchimento")
    print("=" * 50)
    
    cookie_manager = stx.CookieManager()
    
    # Armazenar cookie
    usina_teste = 'PCH-PEDRAS'
    senha_teste = 'pedras25'
    expiracao = datetime.now() + timedelta(days=10)
    cookie_manager.set(usina_teste, senha_teste, expires_at=expiracao)
    
    # Simular lógica de auto-fill
    todos_cookies = cookie_manager.get_all()
    senha_padrao = todos_cookies.get(usina_teste, "")
    
    assert senha_padrao == senha_teste, \
        f"❌ Falha: Esperava '{senha_teste}', obteve '{senha_padrao}'"
    
    print(f"✓ Auto-fill funcionando: {usina_teste} → {senha_padrao}")
    
    # Testar usina sem cookie
    usina_sem_cookie = 'USINA-INEXISTENTE'
    senha_vazia = todos_cookies.get(usina_sem_cookie, "")
    
    assert senha_vazia == "", \
        f"❌ Falha: Esperava string vazia, obteve '{senha_vazia}'"
    
    print(f"✓ Usina sem cookie retorna vazio corretamente")
    print("\n✅ TESTE 4 PASSOU\n")


# -------------------------------------------------------------------
# EXECUÇÃO
# -------------------------------------------------------------------
if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("INICIANDO TESTES DO SISTEMA DE SESSÃO")
    print("=" * 50 + "\n")
    
    try:
        test_cookie_storage()
        test_cookie_expiration()
        test_multiple_usinas()
        test_auto_fill()
        
        print("=" * 50)
        print("✅ TODOS OS TESTES PASSARAM")
        print("=" * 50)
        
    except AssertionError as e:
        print("\n" + "=" * 50)
        print(f"❌ TESTE FALHOU: {e}")
        print("=" * 50)
    except Exception as e:
        print("\n" + "=" * 50)
        print(f"❌ ERRO INESPERADO: {e}")
        print("=" * 50)
