from typing import Dict
import streamlit as st
from datetime import datetime
import plotly.graph_objects as go
import pandas as pd
import numpy as np


def create_energy_card(description, value, data_hora, medida, percentual, value_max=None, value_min=None):
    """
    Creates a styled card displaying energy production information.
    
    Parameters:
    description (str): The description text (e.g., "Produção Energia - 09/2025")
    value (str): The value to display (e.g., "60 MWh")
    
    Returns:
    None: Displays the card directly in the Streamlit app
    """
    # Apply the dark card style
    card_style = """
        <style>
        .energy-card {
            background-color: #1E1E1E;
            color: white;
            padding: 20px;
            border-radius: 20px;
            margin: 10px 0px;
            max-width: 500px;
        }
        .description {
            font-size: 20px;
            font-weight: 500;
            margin-bottom: 10px;
        }
        .value {
            font-size: 32px;
            font-weight: 600;
        }
        .percentual {
            font-size: 14px;
            color: #A8EF6A;
            font-weight: 500;
        }
        </style>
    """
    
    # Create HTML for the card
    if value_max is not None and value_min is not None:
        max_min = f"Máx: {value_max} - Mín: {value_min}"
    else:
        max_min = ""
    if percentual is not None:
        # preciso do icon verde ou vermelho
        cor = "#A8EF6A" if percentual > 0 else "#EF6A6A"
        icon_color = "🔼" if percentual > 0 else "🔽"
        percentual = f"{icon_color} {percentual} cm"
        
    else:
        percentual = ""
        cor = "#808495"

    card_html = f"""
        <div class="energy-card">
            <div class="description">{description} - <span style="font-size: 14px; color: #808495;">Atual.: {data_hora}</span></div>
            <div class="value"> 
                {value} 
                <span style="font-size: 20px; color: #808495;">{medida}</span>
                <span style="font-size: 14px; color: #3A608F;">{max_min}</span>
                <span style="font-size: 14px; color: {cor};">{percentual}</span>
            </div>
        </div>
    """
    return st.markdown(card_style + card_html, unsafe_allow_html=True)


def calculadora_ganho(energia_gerada: float = 0, valor_megawatt: float = 450):
    """
    Calcula o ganho de energia em reais.
    """
    st.markdown("""
        <style>
        /* Container da Calculadora */
        .calculadora-container {
            background-color: rgba(30, 30, 30, 0.8);
            border-radius: 8px;
            padding: 1.5rem;
            margin: 1rem 1rem;
            backdrop-filter: blur(10px);
        }
        
        /* Campos de entrada */
        .stNumberInput > div > div {
            background-color: #1E1E1E !important;
            border: 1px solid #3E3E3E !important;
            color: white !important;
        }
        
        /* Resultado */
        .resultado-calculadora {
            background-color: #2E2E2E;
            border-radius: 8px;
            padding: 1rem;
            margin-top: 1rem;
            text-align: center;
        }
        
        .resultado-valor {
            color: #4C6EF5;
            font-size: 1.5rem;
            font-weight: 500;
            margin: 0;
        }
        
        .resultado-texto {
            color: #808495;
            font-size: 0.85rem;
            margin-top: 0.25rem;
        }
        </style>
    """, unsafe_allow_html=True)

    with st.container():
        energia = st.number_input("Energia gerada (MWh)", value=energia_gerada, key="energia_gerada")
        valor = st.number_input("Valor do megawatt (R$)", value=valor_megawatt, key="valor_megawatt")
        
        try:
            # Calcula o ganho inicial
            ganho = energia * valor
            
            # Se o botão for clicado, recalcula com os valores atuais
            if st.button("Calcular"):
                energia = st.session_state.energia_gerada
                valor = st.session_state.valor_megawatt
                ganho = energia * valor
            
            st.markdown(f"""
                <div class="resultado-calculadora">
                    <p class="resultado-valor">R$ {ganho:,.2f}</p>
                    <p class="resultado-texto">Ganho estimado</p>
                </div>
            """, unsafe_allow_html=True)
            
        except ValueError:
            st.error("Por favor, insira valores numéricos válidos")





def criar_grafico_nivel(df, colunas_nivel, coluna_data=None, titulo="Níveis de Água"):
    """
    Cria um gráfico de níveis de água otimizado para visualizar pequenas variações.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame contendo os dados de nível
    colunas_nivel : list
        Lista contendo os nomes das colunas de nível no dataframe
        Ex: ['nivel_montante', 'nivel_jusante']
    coluna_data : str, opcional
        Nome da coluna que contém as datas/horas (se None, usará o índice do dataframe)
    titulo : str, opcional
        Título do gráfico (default: "Níveis de Água")
    """
    # Criar figura
    fig = go.Figure()
    
    # Determinar o eixo X (data/hora)
    if coluna_data and coluna_data in df.columns:
        x_values = df[coluna_data]
    else:
        x_values = df.index
    
    # Remover a coluna de data/hora da lista de colunas de nível, se estiver presente
    colunas_nivel_plot = [col for col in colunas_nivel if col != coluna_data]
    
    # Verificar quais colunas são numéricas
    colunas_numericas = []
    for coluna in colunas_nivel_plot:
        if coluna in df.columns:
            # Verificar se a coluna é numérica
            if np.issubdtype(df[coluna].dtype, np.number):
                colunas_numericas.append(coluna)
                
                # Criar nome de exibição mais amigável
                nome_exibicao = coluna.replace('_', ' ').title()
                
                fig.add_trace(go.Scatter(
                    x=x_values,
                    y=df[coluna],
                    mode='lines',
                    name=nome_exibicao,
                    line=dict(width=2)
                ))
    
    # Calcular limites dinâmicos para o eixo Y apenas com colunas numéricas
    if colunas_numericas:
        # Calcular mínimo e máximo de forma segura
        y_min = df[colunas_numericas].min().min()
        y_max = df[colunas_numericas].max().max()
        
        # Calcular intervalo de forma segura
        intervalo = float(y_max) - float(y_min)
        
        # Definir margem apropriada
        if intervalo < 0.5:
            margem = 0.1
        else:
            # Margem de 2% do intervalo
            margem = intervalo * 0.02
            
        y_min = float(y_min) - margem
        y_max = float(y_max) + margem
    else:
        # Valores padrão se não houver colunas numéricas válidas
        y_min = 0
        y_max = 10
    
    # Configurar layout do gráfico
    fig.update_layout(
        title=titulo,
        xaxis_title='Data/Hora',
        yaxis_title='Nível (m)',
        yaxis=dict(
            range=[y_min, y_max],
            tickformat='.3f',  # Mostrar 3 casas decimais
        ),
        plot_bgcolor='rgb(17, 17, 17)',
        paper_bgcolor='rgb(17, 17, 17)',
        font=dict(color='white'),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=10, r=10, t=50, b=50),
        hovermode='x unified'
    )
    
    return fig