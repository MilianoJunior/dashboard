'''
Conexão com o banco de dados MySQL
'''
import mysql.connector
from mysql.connector import Error
import logging
import pandas as pd
import traceback
from datetime import datetime, timedelta
import time


def desempenho(funcao):
    def wrapper(*args, **kwargs):
        print(f"      Iniciando a função {funcao.__name__}")
        inicio = time.time()
        resultado = funcao(*args, **kwargs)
        fim = time.time()
        print(f"      Tempo de execução: {fim - inicio} segundos")
        print('--------------------------------')
        return resultado
    return wrapper


def conectar_db(host, user, password, database, port):
    try:
        print(f"Conectando ao banco de dados {database} em {host}:{user}, {port}")
        conexao = mysql.connector.connect(host=host, user=user, password=password, database=database, port=port, timeout=10)
        print(f"Conexão estabelecida com sucesso")
        return conexao
    except Error as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None
    
# @desempenho
def read_all_data(conexao, table_name):
    try:
        query = f"SELECT * FROM {table_name}"
        cursor = conexao.cursor()
        cursor.execute(query)
        resultado = cursor.fetchall()
        df = pd.DataFrame(resultado, columns=[i[0] for i in cursor.description])
        return df
    except Error as e:
        return pd.DataFrame({'Erro ao ler dados da tabela': [e]})
    
# @desempenho
def read_where_data(conexao, table_name, date_initial, date_final, colunas='*'):
    try:
        if not colunas == '*':
            colunas = ','.join(colunas)

        query = f"SELECT {colunas} FROM {table_name} WHERE data_hora BETWEEN '{date_initial}' AND '{date_final}'"
        cursor = conexao.cursor()
        cursor.execute(query)
        resultado = cursor.fetchall()
        df = pd.DataFrame(resultado, columns=[i[0] for i in cursor.description])
        return df
    except Error as e:
        return pd.DataFrame({'Erro ao ler dados da tabela': [e]})

# @desempenho
def columns_table(conexao, table_name):
    try:
        query = f"SHOW COLUMNS FROM {table_name}"
        cursor = conexao.cursor()
        cursor.execute(query)
        resultado = cursor.fetchall()   
        df = pd.DataFrame(resultado, columns=[i[0] for i in cursor.description])
        return df
    except Error as e:
        return pd.DataFrame({'Erro ao ler dados da tabela': [e]})

@desempenho
def dados(conexao, table_name, colunas_energia, colunas_nivel, periodo='M', janela=180):
    try:
        # Montar a query
        energia_total = total_gerado(conexao, table_name, colunas_energia)
        nivel, describe_nivel, percentual_nivel = description_nivel(conexao, table_name, colunas_nivel)
        energia_mensal = description_energia(conexao, table_name, colunas_energia, periodo=periodo, janela=janela)
            
        dict_return = {
            'Produção total': {
                'value': round(float(energia_total['total'].values[0]), 2),
                'value_max': None,
                'value_min': None,
                'percentual': None,
                'description': 'Produção total',
                'data_hora': energia_total['data_hora'][0].strftime('%d/%m/%Y %H:%M:%S'),
                'medida': 'MWh',
            },
        }
        
        for value in describe_nivel.columns:
            describe_value = f"Média {value}".replace('_', ' ').replace('nivel', 'nível')

            dict_return[describe_value] = {
                'value': round(float(describe_nivel.loc['mean', value]), 2),
                'value_max': round(float(describe_nivel.loc['max', value]), 2),
                'value_min': round(float(describe_nivel.loc['min', value]), 2),
                'percentual': percentual_nivel,
                'description': describe_value,
                'data_hora': energia_total['data_hora'][0].strftime('%d/%m/%Y %H:%M:%S'),
                'medida': 'm',
            }

        return energia_total, nivel, describe_nivel, energia_mensal, dict_return

    
    except Exception as e:
        print(f"Erro ao calcular dados do card: {str(e)}")
        return {}
    

# @desempenho
def total_gerado(conexao, table_name, colunas):
    try:
        # Montar a query
        cursor = conexao.cursor()
        columns_select = ','.join(colunas)
        if len(colunas) == 2:
            conditions = f"{colunas[1]} IS NOT NULL"
        else:
            conditions = ' AND '.join(f"{col} IS NOT NULL" for col in colunas[1:])
        query = f"SELECT {columns_select} FROM {table_name} WHERE {conditions} ORDER BY {colunas[0]} DESC LIMIT 1"

        # Executar a query
        cursor.execute(query)
        result = cursor.fetchall()
        
        # Obter os nomes das colunas do cursor.description
        column_names = [i[0] for i in cursor.description]
        df = pd.DataFrame(result, columns=column_names)
        df['total'] = df[colunas[1:]].sum(axis=1)

        return df
    
    except Exception as e:
        return pd.DataFrame({'Erro ao ler dados da tabela': [e]})
    

# @desempenho
def description_nivel(conexao, table_name, colunas, tempo=25):
    try:
        # configurar o período de 30 dias e colunas
        date_initial = datetime.now() - timedelta(hours=tempo)
        date_final = datetime.now()
        df_nivel = read_where_data(conexao, table_name, date_initial, date_final, colunas)

        # calcular a variação percentual na ultima hora
        date_initial = datetime.now() - timedelta(minutes=15)
        date_final = datetime.now()
        df_nivel_15min = df_nivel[df_nivel['data_hora'] >= date_initial]
        percentual = df_nivel_15min[colunas[1]].values[-1] - df_nivel_15min[colunas[1]].values[0]
        percentual = round(percentual * 100, 2)

        df_nivel_ = df_nivel.copy()

        df_nivel.drop(columns=['data_hora'], inplace=True)
        describe = df_nivel.describe()

        return df_nivel_, describe, percentual
    except Exception as e:
        return pd.DataFrame({'Erro ao ler dados da tabela': [e]})

# @desempenho
def description_energia(conexao, table_name, colunas, periodo='D', janela=30):
    '''
    Função para descrever os dados de energia
    Retorna:
        df: DataFrame com o valor mensal de energia de todos os meses para cada coluna
    '''
    try:
        # configurar query
        date_initial = datetime.now() - timedelta(days=janela)
        date_final = datetime.now()
        df_original = read_where_data(conexao, table_name, date_initial, date_final, colunas)
        
        df = calcular_energia_acumulada(df_original, colunas, periodo)
        return df
    except Exception as e:
        return pd.DataFrame({'Erro ao ler dados da tabela': [e]})

# @desempenho
def calcular_energia_acumulada(df, colunas, periodo):

    print('periodo', periodo)
    
    if periodo == 'D':
        # Agrupa por dia e pega o último valor de cada dia para cada coluna
        colunas_energia = [col for col in colunas if 'energia' in col]
        df_diario = df.groupby(df['data_hora'].dt.date).last()

        # Calcular a diferença para cada coluna de energia
        for col in colunas_energia:
            for i in range(1,len(df_diario)):
                df_diario.loc[df_diario.index[i], f'prod_{col}'] = df_diario[col].values[i] - df_diario[col].values[i-1]
            
        return df_diario
        
    if periodo == 'M':
        colunas_energia = [col for col in colunas if 'energia' in col]
        
        # Criar chave ano-mês para agrupar corretamente pelos meses
        df['ano_mes'] = df['data_hora'].dt.strftime('%Y-%m')
        
        # Agrupar pela chave ano-mês e pegar o último registro de cada mês
        df_mensal = df.groupby('ano_mes').last()
        
        # Calcular a diferença para cada coluna de energia
        if len(df_mensal) < 6:
            # registrar o mês anterior com o valor 0
            last_month = df_mensal.index[0]
            after_last_month = datetime.strptime(last_month, '%Y-%m') - timedelta(days=30)
            after_last_month = after_last_month.strftime('%Y-%m')
            for col in colunas_energia:
                df_mensal.loc[after_last_month, col] = 0
            df_mensal = df_mensal.sort_index()


        for col in colunas_energia:
            for i in range(1,len(df_mensal)):
                df_mensal.loc[df_mensal.index[i], f'prod_{col}'] = df_mensal[col].values[i] - df_mensal[col].values[i-1]

        # eliminar as linhas que tem None
        df_mensal = df_mensal.dropna(axis=0)

        return df_mensal
        
    return df
    



'''

Com base no dataframe df_original, preciso calcular a energia acumulada que é a diferença entre o valor atual e o valor anterior,
por que o valor retornado sempre é o acumulado (Soma do atual com o anterior).

'''
















