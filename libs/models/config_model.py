# -------------------------------------------------------------------
# FLUXO DO MÓDULO
# 1. load_app_config → Carrega YAML de usinas
# -------------------------------------------------------------------

import yaml


def load_app_config(deploy_mode: bool) -> dict:
    """Carrega configuração das usinas a partir do YAML."""
    config_file_path = "config/usuarios_usinas.yaml"

    with open(config_file_path, "r") as file:
        config = yaml.safe_load(file)

    if not config or "usinas" not in config:
        raise ValueError("Arquivo de configuração inválido: chave 'usinas' não encontrada")

    return config
