import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
from libs.utils.decorators import desempenho


load_dotenv()

class Database:
    def __init__(self):
        self.host = os.getenv('MYSQLHOST')
        self.user = os.getenv('MYSQLUSER')
        self.password = os.getenv('MYSQLPASSWORD')
        self.database = os.getenv('MYSQLDATABASE')
        self.port = os.getenv('MYSQLPORT')
        self.connection = None

    # @desempenho
    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                
            )
            return self.connection
        except Error as e:
            raise Exception(f"Erro ao conectar ao banco de dados: {e}") # Kept original raise

    # @desempenho
    def execute_query(self, query, params=None):
        if self.connection is None:
            self.connect()
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or ())
            self.connection.commit()
            return cursor
        except Error as e:
            self.connection.rollback()
            raise Exception(f"Erro ao executar query: {e}") # Kept original raise
        finally:
            cursor.close()

    # @desempenho
    def fetch_data(self, query, params=None):
        if self.connection is None:
            self.connect()
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or ())
            result = cursor.fetchall()
            columns = [col[0] for col in cursor.description]
            print(columns)
            print(result)
            return [dict(zip(columns, row)) for row in result]
        except Error as e:
            raise Exception(f"Erro ao buscar dados: {e}") # Kept original raise
        finally:
            cursor.close() 

    def close(self):
        if self.connection and self.connection.is_connected():
            try:
                self.connection.close()
            except Error as e:
                pass 
        self.connection = None # Garante que a conexão seja None após tentar fechar