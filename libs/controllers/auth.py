import os
import hashlib
from dotenv import load_dotenv
# from libs.utils.decorators import desempenho # No longer needed
import streamlit as st
import logging

logger = logging.getLogger(__name__)

load_dotenv()

# AuthManager class removed

def logout(): 
    st.session_state.clear()
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

    print(f"Valor de DASH_USER: '{env_user_value}' (Tipo: {type(env_user_value)})") # Added
    print(f"Valor de DASH_PASS_HASH: '{env_pass_hash_stored_value}' (Tipo: {type(env_pass_hash_stored_value)})") # Added
    print(f"Valor de DASH_SALT: '{env_salt_value}' (Tipo: {type(env_salt_value)})") # Added
    print('-' * 100)
    
    # print(f'selected_usina_nome: {selected_usina_nome}')

    if not env_user_value or not env_pass_hash_stored_value or not env_salt_value: # Logic uses new variable names
        logger.error("Credenciais do dashboard (DASH_USER, DASH_PASS_HASH, DASH_SALT) não estão completamente configuradas no .env.")
        return False, None

    # Calcular o hash da senha fornecida usando env_salt_value
    password_hashed = hashlib.sha256((env_salt_value + password).encode('utf-8')).hexdigest()

    if isinstance(username, str):
        username = username.strip()
    if isinstance(env_user_value, str):
        env_user_value = env_user_value.strip()
    if isinstance(password, str):
        password = password.strip()
    if isinstance(env_pass_hash_stored_value, str):
        env_pass_hash_stored_value = env_pass_hash_stored_value.strip()

    if username == env_user_value:
        if selected_usina_nome in usinas_config:
            usina_obj = usinas_config[selected_usina_nome]
            logger.info(f"Usuário '{username}' autenticado com sucesso para a usina '{selected_usina_nome}'.")
            return True, usina_obj
        else:
            logger.warning(f"Usuário '{username}' autenticado, mas a usina '{selected_usina_nome}' não foi encontrada na configuração.")
            return False, None
    else:
        logger.warning(f"Falha na autenticação para o usuário '{username}'.")
        return False, None
    
'''

refactor/initial-mvc-structure
'''