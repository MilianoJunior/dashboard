import os
import hashlib
from dotenv import load_dotenv
# from libs.utils.decorators import desempenho # No longer needed
import streamlit as st
import logging
import yaml
import os
from datetime import datetime
from libs.utils.decorators import desempenho
    
logger = logging.getLogger(__name__)

load_dotenv()

'''
Tenho o seguinte código que faz a conexão para o sistema de dashboard para o streamlit, preste atenção de que se trata 
de um sistema que tem, varias usinas, com varios usuarios e diferentes senhas, a forma que está abaixo é simplificada, mas é bom assim,
menos é mais.

Mas dai surge o problema, 
'''

@desempenho
def register_user(selected_usina_nome):
    config_file_path = "config/usinas_cont.yaml"
    
    with open(config_file_path, "r") as file:
        config = yaml.safe_load(file)
    acesso = config['usinas'][selected_usina_nome]['acesso']
    acesso += 1
    config['usinas'][selected_usina_nome]['acesso'] = acesso
    # salvar o acesso no arquivo
    with open(config_file_path, "w") as file:
        yaml.dump(config, file)
    data_hora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    print('#####'*10)
    print(f"accesso: {config['usinas'][selected_usina_nome]['acesso']}, data: {data_hora}")
    print(f"selected_usina_nome: {selected_usina_nome}")
    print('#####'*10)

@desempenho
def logout(): 
    st.session_state.clear()
    st.rerun()


@desempenho
def authenticate_user(username, password, selected_usina_nome, usinas_config):
    """
    Autentica o usuário com base no nome de usuário, senha e usina selecionada.
    Retorna (True, usina_obj) se autenticado, senão (False, None).
    """
    if isinstance(username, str):
        username = username.strip()
    if isinstance(password, str):
        password = password.strip()
    senhas = {
        'CGH-FAE': 'fae102',
        'CGH-PICADAS-ALTAS': 'picadas104',
        'PCH-PEDRAS': 'pedras25',
        'CGH-APARECIDA': 'aparecida103',
        'CGH-HOPPEN': 'hoppen80',
    }
    print(f"username: {username}, password: {password}, selected_usina_nome: {selected_usina_nome}")
    print(f"senhas.get(selected_usina_nome,False): {senhas.get(selected_usina_nome,False)}")
    if (username == 'admin') and (password == senhas.get(selected_usina_nome,False)):
    # if True:
        # print(f"selected_usina_nome: {selected_usina_nome}")
        register_user(selected_usina_nome)
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


