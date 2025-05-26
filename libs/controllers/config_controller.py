# Conteúdo inicial
import yaml
import os

def load_app_config(deploy_mode: bool):
    config_file_path = "config/usuarios_usinas.yaml"

    if not deploy_mode:
        with open(config_file_path, "r") as file:
            config = yaml.safe_load(file)
    else:
        # In deploy mode, still load the base config, then override with env vars
        with open(config_file_path, "r") as file:
            config = yaml.safe_load(file)

        url = os.getenv('MYSQLHOST')
        user = os.getenv('MYSQLUSER')
        password = os.getenv('MYSQLPASSWORD')
        database = os.getenv('MYSQLDATABASE')
        port = os.getenv('MYSQLPORT')
        
        if config and 'usinas' in config:
            for usina_key in config['usinas']:
                config['usinas'][usina_key]['ip'] = url
                config['usinas'][usina_key]['usuario'] = user
                config['usinas'][usina_key]['senha'] = password
                config['usinas'][usina_key]['database'] = database
                config['usinas'][usina_key]['port'] = port
        else:
            pass 
            
    return config
