import time
import streamlit as st

cont = 0
def desempenho(funcao):
    def wrapper(*args, **kwargs):
        global cont
        cont += 1
        # print(' '*10,f"Iniciando: {funcao.__name__}")
        inicio = time.time()
        resultado = funcao(*args, **kwargs)
        fim = time.time()
        # print(' '*10,f"{cont} - Finalizado: {funcao.__name__} | Tempo: {fim - inicio:.4f} s")
        # print('-'*40)
        return resultado
    return wrapper 

def get_error_cached(name, e: Exception) -> str:
    """
    Versão de get_error para usar em funções com @st.cache_data.
    Não usa widgets do Streamlit, apenas print no terminal.
    """
    import traceback
    error_info = traceback.extract_tb(e.__traceback__)[-1]
    file_name = error_info.filename.split('/')[-1]
    function_name = error_info.name
    error_msg = f"❌ ERRO CACHED - {name} - {function_name} no arquivo {file_name}, linha {error_info.lineno}: {str(e)}"
    print(error_msg)
    # Não pode usar st.error, st.button ou st.stop em funções cached
    # Apenas retorna None ou levanta exceção
    raise e  # Re-lança a exceção para ser tratada fora do cache

def get_error(name, e: Exception) -> str:
    """Versão original com widgets - apenas para funções SEM cache."""
    import traceback
    error_info = traceback.extract_tb(e.__traceback__)[-1]
    file_name = error_info.filename.split('/')[-1]
    function_name = error_info.name
    st.error(f"Erro na função {name} - {function_name} no arquivo {file_name}, linha {error_info.lineno}: {str(e)}")
    if st.button('Voltar'):
        st.session_state.clear()
        st.rerun()
    st.stop()