import os
import hashlib
from dotenv import load_dotenv
from libs.utils.decorators import desempenho

load_dotenv()

class AuthManager:
    @staticmethod
    @desempenho
    def login(username, password):
        env_user = os.getenv('DASH_USER')
        env_pass_hash = os.getenv('DASH_PASS_HASH')
        if not env_user or not env_pass_hash:
            raise Exception('Credenciais não configuradas no .env')
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        env_pass_hash = hashlib.sha256(env_pass_hash.encode()).hexdigest()
        if username == env_user and password_hash == env_pass_hash:
            return True
        return False

    @staticmethod
    @desempenho
    def logout():
        # Apenas um placeholder, pois o controle de sessão será feito na camada de apresentação
        return True 