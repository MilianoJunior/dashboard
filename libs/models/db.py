import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
from libs.utils.decorators import desempenho


load_dotenv()

class Database:
    @desempenho
    def __init__(self):
        self.host = os.getenv('MYSQLHOST')
        self.user = os.getenv('MYSQLUSER')
        self.password = os.getenv('MYSQLPASSWORD')
        self.database = os.getenv('MYSQLDATABASE')
        self.port = os.getenv('MYSQLPORT')
        self.connection_timeout = int(os.getenv('MYSQLCONNECTIONTIMEOUT', 10))
        self.connection = None

    @desempenho 
    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                connection_timeout=self.connection_timeout
            )
            return self.connection
        except Error as e:
            print(f"Erro ao conectar ao banco de dados: {e}")
            raise Exception(f"Erro ao conectar ao banco de dados: {e}") # Kept original raise

    @desempenho
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

    @desempenho
    def fetch_data(self, query, params=None):
        if self.connection is None:
            self.connect()
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or ())
            result = cursor.fetchall()
            columns = [col[0] for col in cursor.description]
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


if __name__ == '__main__':
    try:
        # print('teste de conexão com o banco de dados')
        # db = Database()
        # print('conectando ao banco de dados')
        # db.connect()
        # print('executando query')
        # dados = db.execute_query('SELECT * FROM users')
        # print(dados)
        # print('buscando dados')
        # dados = db.fetch_data('SELECT * FROM users')
        # print(dados)
        import pandas as pd
        from sqlalchemy import create_engine

        # URL de conexão
        db_url = "mysql+pymysql://root:cgG3hDhhc4GcbhF5d2FBf422C-BHhe35@viaduct.proxy.rlwy.net:29893/railway"

        # Cria o engine SQLAlchemy
        engine = create_engine(db_url)

        # Exemplo de consulta
        query = "SELECT * FROM cgh_fae"

        # Lê os dados diretamente para um DataFrame
        df = pd.read_sql(query, engine)

        print(df.head())
    except KeyboardInterrupt:
        print('\nExecução interrompida pelo usuário (Ctrl+C).')
    finally:
        print('fechando conexão')
        # db.close()