import streamlit as st
import sys
import os
import yaml
from datetime import datetime, timedelta
import time
# Adiciona o diretório raiz ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from libs.db import conectar_db, read_all_data, read_where_data, columns_table


def test_conexao_db(config):
    for key, value in config['usinas'].items():
        st.write(f"Testando a usina: {key}")
        ip = value['ip']
        usuario = value['usuario']
        senha = value['senha']
        banco_de_dados = value['database']
        tabela = value['tabela']
        port = value['port']
        inicio = time.time()
        conexao = conectar_db(ip, usuario, senha, banco_de_dados, port)
        if conexao:
            st.success("Conexão estabelecida com sucesso!")
        else:
            st.error("Falha ao conectar ao banco de dados")
        conexao.close()
        fim = time.time()
        st.write(f"Tempo de conexão: {fim - inicio} segundos")

def test_leitura_dados_db(config):
    for key, value in config['usinas'].items():
        st.write(f"Testando a usina: {key}")
        ip = value['ip']
        usuario = value['usuario']
        senha = value['senha']
        banco_de_dados = value['database']
        tabela = value['tabela']
        port = value['port']
        inicio = time.time()
        conexao = conectar_db(ip, usuario, senha, banco_de_dados, port)
        if conexao:
            st.success("Conexão estabelecida com sucesso!") 
            dados = read_all_data(conexao, tabela)
            if dados is not None:
                st.success("Dados lidos com sucesso!")
                st.dataframe(dados.head())
            else:
                st.error("Erro ao ler dados da tabela")
        else:
            st.error("Falha ao conectar ao banco de dados")
        conexao.close()
        fim = time.time()
        st.write(f"Tempo de leitura de dados: {fim - inicio} segundos")


def test_leitura_dados_db_where(config):
    for key, value in config['usinas'].items():
        st.write(f"Testando a usina: {key}")    
        ip = value['ip']
        usuario = value['usuario']
        senha = value['senha']
        banco_de_dados = value['database']
        tabela = value['tabela']
        port = value['port']    
        inicio = time.time()
        conexao = conectar_db(ip, usuario, senha, banco_de_dados, port)
        if conexao:
            st.success("Conexão estabelecida com sucesso!")
            data_inicial = datetime.now() - timedelta(days=30)
            data_final = datetime.now()
            dados = read_where_data(conexao, tabela, data_inicial, data_final)
            if dados is not None:
                st.success("Dados lidos com sucesso!")
                st.dataframe(dados.head())  
        else:
            st.error("Falha ao conectar ao banco de dados")
        conexao.close()
        fim = time.time()
        st.write(f"Tempo de leitura de dados: {fim - inicio} segundos")

def test_colunas_tabela(config):
    for key, value in config['usinas'].items():
        st.write(f"Testando a usina: {key}")
        ip = value['ip']
        usuario = value['usuario']
        senha = value['senha']
        banco_de_dados = value['database']  
        tabela = value['tabela']
        port = value['port']
        inicio = time.time()
        conexao = conectar_db(ip, usuario, senha, banco_de_dados, port)
        if conexao:
            st.success("Conexão estabelecida com sucesso!")
            colunas = columns_table(conexao, tabela)
            if colunas is not None:
                st.success("Colunas lidas com sucesso!")
                st.dataframe(colunas.head())
        else:
            st.error("Falha ao conectar ao banco de dados")
        conexao.close()
        fim = time.time()
        st.write(f"Tempo de leitura de colunas: {fim - inicio} segundos")


def main():
    st.title("Teste de Conexão com Banco de Dados")
    
    # Obtém o caminho absoluto do diretório raiz
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(root_dir, "config", "usuarios_usinas.yaml")
    
    try:
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)
            
        test_conexao_db(config)
        test_leitura_dados_db(config)
        test_leitura_dados_db_where(config)
        test_colunas_tabela(config)
    except FileNotFoundError:
        st.error(f"Arquivo de configuração não encontrado em: {config_path}")
    except Exception as e:
        st.error(f"Erro ao carregar configuração: {str(e)}")

if __name__ == "__main__":
    main()









