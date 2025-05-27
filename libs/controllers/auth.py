import os
import hashlib
from dotenv import load_dotenv
# from libs.utils.decorators import desempenho # No longer needed
import streamlit as st
import logging

logger = logging.getLogger(__name__)

load_dotenv()

# AuthManager class removed

def logout(): # Modified function
    logger.info("Iniciando processo de logout.")
    if 'db' in st.session_state and hasattr(st.session_state['db'], 'close'):
        try:
            logger.info("Fechando conexão do banco de dados (st.session_state['db'].close()).")
            st.session_state['db'].close()
        except Exception as e:
            logger.error(f"Erro ao fechar a conexão do banco de dados durante o logout: {e}", exc_info=True)
    
    logger.info("Limpando st.session_state.")
    st.session_state.clear()
    # Adicionar st.session_state['logado'] = False explicitamente após o clear pode ser uma boa prática
    # para garantir que o estado de login seja resetado mesmo que o rerun() falhe ou seja interrompido.
    st.session_state['logado'] = False 
    logger.info("Redirecionando após logout.")
    st.rerun()

def authenticate_user(username, password, selected_usina_nome, usinas_config):
    """
    Autentica o usuário com base no nome de usuário, senha e usina selecionada.
    Retorna (True, usina_obj) se autenticado, senão (False, None).
    """
    logger.info(f"Tentando ler variáveis de ambiente para autenticação:") # Added
    env_user_value = os.getenv('DASH_USER') # Changed variable name
    env_pass_hash_stored_value = os.getenv('DASH_PASS_HASH') # Changed variable name
    env_salt_value = os.getenv('DASH_SALT') # Changed variable name

    logger.info(f"Valor de DASH_USER: '{env_user_value}' (Tipo: {type(env_user_value)})") 
    logger.info(f"Valor de DASH_PASS_HASH: '{env_pass_hash_stored_value}' (Tipo: {type(env_pass_hash_stored_value)})") 
    logger.info(f"Valor de DASH_SALT: '{env_salt_value}' (Tipo: {type(env_salt_value)})") 

    # Detailed Authentication Debugging Block - START
    logger.info(f"--- Início da Depuração Detalhada da Autenticação ---") # Added
    logger.info(f"Entrada - Username: '{username}'") # Added
    logger.info(f"Entrada - Password (texto plano): '{password}'") # Added - REMINDER: Remove/disable post-debug
    # End of new initial logs for detailed debugging

    if not env_user_value or not env_pass_hash_stored_value or not env_salt_value: 
        logger.error("Credenciais do dashboard (DASH_USER, DASH_PASS_HASH, DASH_SALT) não estão completamente configuradas no .env.")
        logger.info(f"--- Fim da Depuração Detalhada da Autenticação (Falha Prematura) ---") # Added
        return False, None

    logger.info(f"Salt do Ambiente (usado para hashear a entrada): '{env_salt_value}'") # Added
    # Calcular o hash da senha fornecida usando env_salt_value
    password_hashed = hashlib.sha256((env_salt_value + password).encode('utf-8')).hexdigest()
    logger.info(f"Hash Calculado (da entrada + salt): '{password_hashed}'") # Added

    # Reconfirm environment values for comparison
    logger.info(f"Valor Esperado do Ambiente - Username: '{env_user_value}'") # Added
    logger.info(f"Valor Esperado do Ambiente - Hash da Senha: '{env_pass_hash_stored_value}'") # Added
    logger.info(f"--- Fim da Depuração Detalhada da Autenticação ---") # Added
    # End of detailed Authentication Debugging Block

    # Comparar usando env_user_value e env_pass_hash_stored_value
    if username == env_user_value and password_hashed == env_pass_hash_stored_value:
        if selected_usina_nome in usinas_config:
            usina_obj = usinas_config[selected_usina_nome]
            logger.info(f"Usuário '{username}' autenticado com sucesso para a usina '{selected_usina_nome}'.")
            return True, usina_obj
        else:
            logger.warning(f"Usuário '{username}' autenticado, mas a usina '{selected_usina_nome}' não foi encontrada na configuração.")
            return False, None
    else:
        logger.warning(f"Falha na autenticação para o usuário '{username}'. Comparado '{password_hashed}' (calculado) com '{env_pass_hash_stored_value}' (esperado).") # Enhanced existing log
        return False, None