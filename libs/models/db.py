import logging # Added
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
from libs.utils.decorators import desempenho

logger = logging.getLogger(__name__) # Added

load_dotenv()

class Database:
    def __init__(self):
        self.host = os.getenv('MYSQLHOST')
        self.user = os.getenv('MYSQLUSER')
        self.password = os.getenv('MYSQLPASSWORD')
        self.database = os.getenv('MYSQLDATABASE')
        self.port = os.getenv('MYSQLPORT')
        self.connection = None

    @desempenho
    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port
            )
            logger.info(f"Conectado ao banco de dados {self.database} em {self.host}") # Added
            return self.connection
        except Error as e:
            logger.error(f"Erro ao conectar ao banco de dados {self.database} em {self.host}: {e}", exc_info=True) # Added
            raise Exception(f"Erro ao conectar ao banco de dados: {e}") # Kept original raise

    @desempenho
    def execute_query(self, query, params=None):
        if self.connection is None:
            self.connect()
        cursor = self.connection.cursor()
        try:
            logger.debug(f"Executando query: {query[:100]}... com params: {params}") # Added
            cursor.execute(query, params or ())
            self.connection.commit()
            return cursor
        except Error as e:
            self.connection.rollback()
            logger.error(f"Erro ao executar query '{query[:100]}...': {e}", exc_info=True) # Added
            raise Exception(f"Erro ao executar query: {e}") # Kept original raise
        finally:
            cursor.close()

    @desempenho
    def fetch_data(self, query, params=None):
        if self.connection is None:
            self.connect()
        cursor = self.connection.cursor()
        try:
            logger.debug(f"Buscando dados com query: {query[:100]}... com params: {params}") # Added
            cursor.execute(query, params or ())
            result = cursor.fetchall()
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in result]
        except Error as e:
            logger.error(f"Erro ao buscar dados com query '{query[:100]}...': {e}", exc_info=True) # Added
            raise Exception(f"Erro ao buscar dados: {e}") # Kept original raise
        finally:
            cursor.close() 

    def close(self):
        if self.connection and self.connection.is_connected():
            try:
                self.connection.close()
                logger.info(f"Conexão ao MySQL ({self.database}@{self.host}) fechada.") # Changed from print to logger
            except Error as e:
                logger.warning(f"Erro ao fechar a conexão MySQL ({self.database}@{self.host}): {e}", exc_info=True) # Changed from print to logger
                pass 
        self.connection = None # Garante que a conexão seja None após tentar fechar