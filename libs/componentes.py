from typing import Dict
import streamlit as st
from datetime import datetime
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import plotly.express as px

def create_energy_card(description, value, data_hora, medida, percentual, value_max=None, value_min=None):
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
        cor = "#A8EF6A" if percentual > 0 else "#EF6A6A"
        icon_color = "🔼" if percentual > 0 else "🔽"
        if medida == 'MWh':
            percentual = f"{icon_color} {percentual} %"
        else:
            percentual =f"{icon_color} {percentual} m"
        
    else:
        percentual = ""
        cor = "#808495"

    card_html = f"""
        <div class="energy-card">
            <div class="description">{description}<span style="font-size: 14px; color: #808495;"></div>
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

def create_widget_temperatura(df):
    try:
        cols = st.columns(5)
        icons = {
            'oleo_uhlm': '🔥',
            'oleo_uhrv': '🔥',
            'casq_comb': '⚙️',
            'manc_casq_esc': '⚙️',
            'enrol_a': '⚡',
            'enrol_b': '⚡',
            'enrol_c': '⚡',
            'nucleo_estator_01': '🧲',
            'nucleo_estator_02': '🧲',
            'nucleo_estator_03': '🧲'
        }
        for i, col in enumerate(df.columns):
            with cols[i % 5]:
                mean_value = round(float(df.loc['mean', col]), 2)
                min_value = round(float(df.loc['min', col]), 2)
                max_value = round(float(df.loc['max', col]), 2)
                icon = icons.get(col, '🌡️')
                st.markdown(
                    f"""
                    <div style="
                        background-color: #1E1E1E; 
                        border-radius: 10px; 
                        padding: 10px; 
                        margin-bottom: 10px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    ">
                        <div style="font-size: 12px; color: #CCCCCC; margin-bottom: 5px;">
                            Temp {col.replace('_', ' ')}
                        </div>
                        <div style="
                            display: flex; 
                            justify-content: space-between; 
                            align-items: center;
                        ">
                            <span style="font-size: 28px; font-weight: bold; color: white;">
                                {mean_value}°
                            </span>
                            <span style="font-size: 24px;">
                                {icon}
                            </span>
                        </div>
                        <div style="
                            font-size: 11px;
                            color: #AAAAAA;
                            margin-top: 5px;
                            display: flex;
                            justify-content: space-between;
                        ">
                            <span>Min: {min_value}°</span>
                            <span>Max: {max_value}°</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    except Exception as e:
        st.error(f'Erro ao criar widget de temperatura: {e}')

def menu_principal(config, usina):
    col1, col2, col3, col4 = st.columns([1, 6, 1, 4])
    with col1:
        st.markdown(f"<div style='width: 15%;'>", unsafe_allow_html=True)
        st.image("assets/logo.png", width=80)
        st.markdown(f"</div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<h2 style='text-align: left; margin-top: 0;'>Dashboard {st.session_state['usina']['tabela'].replace('_', ' ').capitalize()}</h2>", unsafe_allow_html=True)
    with col3:
        st.write(" ")
        logout_btn = st.button("Logout", use_container_width=True)
        if logout_btn:
            st.session_state.clear()
            st.rerun()

def create_grafico_producao_energia(df):
    colunas_prod = [col for col in st.session_state.ultimos_30_dias.columns if col.startswith('prod_')]
    fig = px.bar(
        st.session_state.ultimos_30_dias,
        x='data_hora',
        y=colunas_prod,
        title='Produção de Energia',
        barmode='group',
        height=500
    )
    fig.update_layout(
        xaxis_title='Data/Hora',
        yaxis_title='Energia (MWh)',
        legend_title='Unidades Geradoras'
    )
    st.plotly_chart(fig, use_container_width=True)

def create_grafico_nivel(df):
    colunas_nivel = [col for col in df.columns if 'niv' in col]
    fig = px.line(df, x='data_hora', y=colunas_nivel, title='Nível')
    nivel_vertimento = float(st.session_state['usina']['nivel_vertimento'])
    fig.add_hline(y=nivel_vertimento, line_dash="dash", line_color="red", 
                  annotation_text="Nível de Vertimento", annotation_position="right")
    fig.update_layout(
        yaxis_title='Nível (m)',
        showlegend=True
    )
    st.plotly_chart(fig, use_container_width=True)