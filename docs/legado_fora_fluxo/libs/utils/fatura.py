# from fpdf import FPDF
# from datetime import datetime
# from dotenv import load_dotenv
# import os
# import webbrowser
# import pandas as pd
# import numpy as np
# import seaborn as sns
# import matplotlib.pyplot as plt
# from matplotlib.ticker import FormatStrFormatter
# import traceback

# load_dotenv()

# info = {
#     "Nome :": os.getenv('NOME_USINA'),
#     "Número de Turbinas :": os.getenv('NUMERO_TURBINAS'),
#     "Estado :": os.getenv('ESTADO'),
#     "Data Atual :": datetime.now().strftime("%Y-%m-%d"),
#     "Localização :": os.getenv('LOCALIZACAO'),
#     "Potência :": os.getenv('POTENCIA'),
# }

# engesep= {
#     "title": 'EngeSEP Engenharia Integrada LTDA',
#     "endereco": 'R. Roque Domingos Onghero, no 30d - Bom Retiro,Chapecó-SC',
#     "CNPJ": 'CNPJ: 22.248.519/0001-26',
#     "telefone":'(49)-991075958',
#     "email": 'engesep@engesep.com.br'
# }

# DIR = os.path.dirname(os.path.abspath(__file__))
# class PDF(FPDF):

#     def __init__(self, info, dfs, logger=None):
#         self.info = info
#         self.dfs = dfs
#         super().__init__()
#         self.orientation = 'P'
#         self.unit = 'mm'
#         self.format = 'A4'
#         self.fonte = 'helvetica'
#         self.resolucao = int(2)
#         self.logger = logger

#     def error(self, err):
#         tb = traceback.extract_tb(err.__traceback__)
#         filename = tb[-1].filename
#         line_no = tb[-1].lineno
#         method_name = tb[-1].name
#         msg = f"Erro: {err} - {filename} - {line_no} - {method_name}"
#         if self.logger:
#             self.logger.error(msg)
#         else:
#             print(msg)
#         raise Exception(msg)

#     def compose(self):
#         try:
#             for key, value in self.dfs.items():
#                 if 'energia' in key:
#                     self.grafico_energia(value['values'])
#                 if 'nivel' in key:
#                     self.grafico_nivel(value['values'])
#             for key, value in self.dfs.items():
#                 if 'energia' in key:
#                     self.add_paginas(value)
#         except Exception as e:
#             self.error(e)
#     def add_paginas(self, values):
#         try:
#             name = values['values'].columns[0]
#             UG = name.split('_')[0].upper()
#             title = f"Relatório - EngeSEP  {UG}" # - {UG}
#             self.add_page()
#             self.chapter_title(title)
#             self.sub_title('Informações Gerais')
#             self.simple_table()
#             self.sub_title('Informações quantitativas')
#             self.chapter_body(values['statistics'], UG)
#         except Exception as e:
#             self.error(e)

#     def header(self):
#         try:
#             self.set_margins(20, 20, 20)
#             img_path = os.path.join(DIR, '..', '..', 'assets', 'login.png')
#             fonte = "helvetica"
#             img_x = 20
#             img_y = 20
#             img_h = 20  # altura da imagem em mm
#             self.image(img_path, img_x, img_y, h=img_h)

#             # Posição inicial do texto à direita da imagem
#             text_x = img_x + 25  # espaço após a imagem
#             text_y = img_y
#             self.set_xy(text_x, text_y)
#             self.set_font(fonte, 'B', 11)
#             self.set_text_color(18, 27, 44)
#             self.cell(0, 5, engesep["title"], ln=1)
#             self.set_x(text_x)
#             self.set_font(fonte, '', 10)
#             self.cell(0, 5, engesep["endereco"], ln=1)
#             self.set_x(text_x)
#             self.cell(0, 5, engesep["CNPJ"], ln=1)
#             self.set_x(text_x)
#             self.set_font(fonte, '', 9)
#             self.cell(0, 5, f"{engesep['telefone']}    {engesep['email']}", ln=1)
#             self.ln(8)
#         except Exception as e:
#             self.error(e)

#     def grafico_energia(self, dados):
#         try:
#             # Plotando o gráfico
#             # Convert the index to datetime if it's not already
#             if not isinstance(dados.index, pd.DatetimeIndex):
#                 dados.index = pd.to_datetime(dados.index)

#             # Now you can format it as you like
#             dados.index = dados.index.strftime('%d/%m')

#             # Index(['22/01', '23/01', '24/01', '25/01'], dtype='object', name='data_hora')
#             name = dados.columns[0]
#             sns.set_theme(style="whitegrid")
#             f, ax = plt.subplots(figsize=(6, 13))
#             # ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
#             sns.set_color_codes("pastel")
#             sns.barplot(x=name, y=dados.index, data=dados, label="Energia em MW/h", color="b")
#             ax.bar_label(ax.containers[0], label_type='center')
#             ax.legend(ncol='', loc="lower right", frameon=True)
#             UG = name.split('_')[0].upper()
#             ax.set(xlim=(0, max(dados[name].values)), ylabel="Dias do mês",
#                    xlabel="Geração de Energia em MW/h", title=f'Geração de energia: {UG}')
#             sns.despine(left=True, bottom=True)

#             arquivo = UG+'.png'
#             energia_img = os.path.join(DIR, '..', 'assets', arquivo)
#             plt.savefig(energia_img, bbox_inches='tight')
#         except Exception as e:
#             self.error(e)

#     def grafico_nivel(self, dados):
#         try:
#             dados.index = dados.index.strftime('%d')
#             name = dados.columns[0]
#             sns.set_style("whitegrid")
#             f, ax = plt.subplots(figsize=(10, 9))
#             sns.set_color_codes("pastel")
#             g = sns.relplot(x=dados.index, y=name, kind="line", errorbar="sd", markers=True, data=dados).set_titles(
#                 "Nível do reservatório de águas")
#             g.set_axis_labels("Dias do mês", "Volume de águas em metros")

#             # Rotaciona as etiquetas e configura o espaçamento entre elas
#             g.set_xticklabels(rotation=45)

#             num_points = len(dados.index)
#             every_nth = 5
#             g.set(xticks=dados.index[::every_nth])

#             self.nivel_img = os.path.join(DIR, '..', 'assets', 'nivel.png')
#             plt.savefig(self.nivel_img, bbox_inches='tight')
#             plt.close()
#         except Exception as e:
#             self.error(e)

#     def chapter_title(self, title):
#         try:
#             self.set_font(self.fonte, 'B', 12)
#             self.set_text_color(244, 244, 244)
#             self.set_fill_color(10, 10, 10)
#             self.cell(0, 6, title, 0, 1, 'L', True)
#             self.ln(4)
#         except Exception as e:
#             self.error(e)

#     def sub_title(self, label):
#         try:
#             self.set_font(self.fonte, '', 10)
#             self.set_fill_color(18, 27, 44)
#             self.set_text_color(255, 246, 247)
#             self.cell(0, 5,label, 0, 1, 'L', 1)
#             self.ln(1)
#         except Exception as e:
#             self.error(e)

#     def simple_table(self, spacing=1):
#         try:
#             self.set_text_color(18, 27, 44)
#             self.set_font(self.fonte, size=10)
#             line_height = self.font_size * 1.5
#             col_width_ = round(self.epw / 2,2) # distribute content evenly
#             data = []
#             for key, value in self.info.items():
#                 data.append([key, value])
#             for row in data:
#                 for datum in row:
#                     col_width = round(max(40, self.get_string_width(datum) +5),2)
#                     self.multi_cell(col_width, line_height, datum, border=0, ln=3, align='L', max_line_height=self.font_size)
#                 self.ln(line_height)
#             self.ln(1)
#         except Exception as e:
#             self.error(e)

#     def chapter_body(self, stats, UG):
#         try:
#             arquivo = UG+'.png'
#             energia_img = os.path.join(DIR, '..', 'assets', arquivo)
#             self.image(energia_img, 100, 108, 87)
#             self.set_font(self.fonte, '', 8)
#             self.set_text_color(244, 244, 244)
#             self.set_fill_color(10, 10, 10)
#             self.cell(80, 5,'Relatório de energia', 0, 0, 'L', True)
#             self.ln()
#             self.set_fill_color(243, 245, 247)
#             self.set_text_color(18, 27, 44)
#             for key, value in stats.items():
#                 self.cell(80, 5, key+': '+str(round(value[0],self.resolucao))+' MW/h', 0, 0, 'L', True)
#                 self.ln()
#             self.set_text_color(244, 244, 244)
#             self.set_fill_color(10, 10, 10)
#             self.cell(80, 5,'Relatório de nível de águas', 0, 0, 'L', True)
#             self.ln()
#             self.set_fill_color(243, 245, 247)
#             self.set_text_color(18, 27, 44)
#             for key, value in self.dfs.items():
#                 if 'nivel' in key:
#                     for key, value in value['statistics'].items():
#                         self.cell(80, 5, key+': '+str(round(value[0],self.resolucao))+' m', 0, 0, 'L', True)
#                         self.ln()
#             self.set_text_color(244, 244, 244)
#             self.set_fill_color(10, 10, 10)
#             self.cell(80, 5,'Gráfico nível de águas', 0, 0, 'L', True)
#             self.ln()
#             self.ln(10)
#             ly = self.get_y()
#             self.image(self.nivel_img,20,round(ly), 80)
#         except Exception as e:
#             self.error(e)

#     def footer(self):
#         try:
#             data_atual = datetime.now()
#             data_e_hora = data_atual.strftime('%d/%m/%Y %H:%M')
#             self.set_fill_color(243, 245, 247)
#             self.set_y(-15)
#             self.set_font(self.fonte, 'I', 8)
#             self.set_text_color(128)
#             self.cell(0, 10, 'relatório gerado em '+str(data_e_hora)+ ' Página ' + str(self.page_no()), 0, 0, 'C')
#             self.ln(3)
#             self.cell(0, 10, 'Os valores referentes à produção de energia são obtidos a partir de dados operacionais.', 0, 0, 'C')
#         except Exception as e:
#             self.error(e)

import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

def generate_report_pdf():
    """
    Gera um relatório em PDF com base nos dados extraídos da imagem.
    """
    doc = SimpleDocTemplate("relatorio_engesep.pdf", pagesize=letter,
                            rightMargin=40, leftMargin=40,
                            topMargin=40, bottomMargin=28)
    story = []
    styles = getSampleStyleSheet()

    # Estilos personalizados
    styles.add(ParagraphStyle(name='TableHeader', alignment=TA_CENTER, fontSize=10, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='TableBody', alignment=TA_CENTER, fontSize=9, fontName='Helvetica'))
    styles.add(ParagraphStyle(name='RightAlign', alignment=TA_RIGHT, fontName='Helvetica'))
    styles.add(ParagraphStyle(name='LeftAlign', alignment=TA_LEFT, fontName='Helvetica'))
    styles.add(ParagraphStyle(name='SectionTitle', fontSize=11, fontName='Helvetica-Bold',
                              textColor=colors.white, backColor='#44546A',
                              leading=14, padding=(4, 4)))
    styles.add(ParagraphStyle(name='FooterBox', alignment=TA_LEFT, fontSize=8, fontName='Helvetica'))


    # --- Cabeçalho ---
    header_data = [
        [Paragraph('<b>EngeSEP</b>', styles['LeftAlign']),
         Paragraph('48 991879998 | www.engesep.com.br | om@engesep.com.br', styles['RightAlign'])]
    ]
    header_table = Table(header_data, colWidths=[2.5*inch, 4.5*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.2*inch))

    # --- Informações do Empreendimento e Fatura ---
    info_data = [
        [Paragraph('<b>UNIDADE CONSUMIDORA</b><br/>NÃO INFORMADO', styles['LeftAlign']),
         Paragraph('<b>DEMONSTRATIVO</b>', styles['LeftAlign'])],
        ['', [
             Paragraph('<b>Nº DA FATURA:</b> 2025-6', styles['LeftAlign']),
             Paragraph('<b>Data de Vencimento:</b> 19/07/2025', styles['LeftAlign']),
             Paragraph('<b>Referência:</b> jun/25', styles['LeftAlign']),
            ]
        ]
    ]
    info_table = Table(info_data, colWidths=[3.5*inch, 3.5*inch])
    info_table.setStyle(TableStyle([
        ('BOX', (0, 0), (0, 0), 1, colors.grey),
        ('BOX', (1, 0), (1, -1), 1, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('SPAN', (0,0), (0,1)),
    ]))
    story.append(Paragraph('Empreendimento<br/><b>CGH PICADAS ALTAS</b>', styles['LeftAlign']))
    story.append(Spacer(1, 0.1*inch))
    story.append(info_table)
    story.append(Spacer(1, 0.2*inch))

    # --- Resultados de Produção ---
    story.append(Paragraph('Resultados de Produção', styles['SectionTitle']))
    story.append(Spacer(1, 0.15*inch))

    # Tabela de Geração
    prod_data = [
        [Paragraph('<b>Referência</b>', styles['TableBody']), Paragraph('<b>Geração - MWH</b>', styles['TableBody'])],
        ['jun/25', '149,00'],
        ['mai/25', '88,88'],
        ['abr/25', '36,91'],
        ['mar/25', ''],
        ['fev/25', ''],
        ['jan/25', ''],
        ['dez/24', ''],
        ['nov/24', ''],
        ['out/24', ''],
        ['set/24', ''],
        ['ago/24', ''],
        ['jul/24', ''],
    ]
    prod_table = Table(prod_data, colWidths=[1.0*inch, 1.2*inch])
    prod_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))

    # Gráfico de Geração
    labels = ['abr/25', 'mai/25', 'jun/25']
    geracao = [36.91, 88.88, 149.00]
    
    fig, ax = plt.subplots(figsize=(4, 2.5))
    bars = ax.bar(labels, geracao, color=['#4472C4', '#4472C4', '#4472C4'])
    ax.set_ylabel('Geração - MWH')
    ax.set_ylim(0, max(geracao) * 1.2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 3, f'{yval:,.2f}'.replace(',', '.'), ha='center', va='bottom', fontsize=8)

    chart_path = "geracao_chart.png"
    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    chart_image = Image(chart_path, width=4.0*inch, height=2.5*inch)

    # Tabela combinada Produção e Gráfico
    prod_chart_data = [[prod_table, chart_image]]
    prod_chart_table = Table(prod_chart_data, colWidths=[2.3*inch, 4.2*inch])
    prod_chart_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    story.append(prod_chart_table)
    story.append(Spacer(1, 0.1*inch))
    
    # Tabela Acumulado
    acum_data = [
        ['Ano', '2023', '2024', '2025'],
        ['Acumulado (MWh)', '', '', '275']
    ]
    acum_table = Table(acum_data, colWidths=[1.5*inch] * 4)
    acum_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (0,1), 'Helvetica-Bold'),
    ]))
    story.append(acum_table)
    story.append(Spacer(1, 0.2*inch))


    # --- Orientações Técnicas ---
    story.append(Paragraph('Orientações Técnicas/ Melhorias para aumentar desempenho do Empreendimento', styles['SectionTitle']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("1º - Reforço contra enchentes - Conforme eventos ocorridos em 19/06/2025 - Risco de Alagamento Casa de Força e demais estruturas", styles['LeftAlign']))
    story.append(Spacer(1, 0.2*inch))

    # --- Financeiro ---
    story.append(Paragraph('Financeiro', styles['SectionTitle']))
    story.append(Spacer(1, 0.15*inch))
    
    fin_data = [
        [Paragraph('<b>Referência</b>', styles['TableBody']), Paragraph('<b>Valor (R$) Mensal</b>', styles['TableBody']), Paragraph('<b>Serviços Extras</b>', styles['TableBody']),
         Paragraph('<b>Data Vencimento</b>', styles['TableBody']), Paragraph('<b>Status</b>', styles['TableBody']), Paragraph('<b>Total (R$)</b>', styles['TableBody'])],
        ['jun/25', 'R$ 7.000,00', '', '10/07/2025', 'Bônus', ''],
        ['mai/25', 'R$ 7.000,00', '', '19/06/2025', 'Bônus', ''],
        ['abr/25', 'R$ 7.000,00', '', '19/05/2025', 'Bônus', ''],
        ['mar/25', '', '', '', '', ''],
        ['fev/25', '', '', '', '', ''],
        ['jan/25', '', '', '', '', ''],
        ['out/24', '', '', '', '', ''],
        ['set/24', '', '', '', '', ''],
    ]
    fin_table = Table(fin_data, colWidths=[0.8*inch, 1.2*inch, 1.0*inch, 1.2*inch, 0.8*inch, 1.0*inch])
    fin_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(red=(220/255), green=(230/255), blue=(241/255))),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (-1, -1), 9)
    ]))
    story.append(fin_table)
    story.append(Spacer(1, 0.3*inch))

    # --- Rodapé ---
    # Placeholder para QR Code
    qr_placeholder = np.zeros((100, 100), dtype=np.uint8)
    qr_placeholder_path = "qr_placeholder.png"
    plt.imsave(qr_placeholder_path, qr_placeholder, cmap='gray')
    qr_image = Image(qr_placeholder_path, width=0.8*inch, height=0.8*inch)
    
    deposito_info = """
    <b>Dados para Depósito</b><br/>
    Banco Sicredi: 756<br/>
    Ag:0258 / CC 14938-5<br/>
    PIX: 22.248.519-0001-26
    """
    
    contrato_info = """
    <b>Contrato N°:</b> EGOM-8500-R0A<br/>
    <b>Início / Fim:</b> 19/04/2025 - 19/04/2030
    """

    total_data = [
        ['Mensalidade O&M', 'R$ 0,00'],
        ['Serviços Extras', 'R$ 0,00'],
        ['Outros', 'R$ 0,00'],
        ['<b>TOTAL</b>', '<b>R$ 0,00</b>']
    ]
    total_table = Table(total_data, colWidths=[1.2*inch, 1.0*inch])
    total_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('BACKGROUND', (0,0), (-1,-1), colors.Color(red=(220/255), green=(230/255), blue=(241/255))),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
    ]))

    footer_data = [
        [[qr_image, Paragraph(deposito_info, styles['FooterBox'])],
         Paragraph(contrato_info, styles['LeftAlign']),
         total_table]
    ]
    
    footer_table = Table(footer_data, colWidths=[2.5*inch, 2.5*inch, 2.3*inch])
    footer_table.setStyle(TableStyle([
       ('VALIGN', (0, 0), (-1, -1), 'TOP'),
       ('ALIGN', (0,0), (0,0), 'LEFT'),
    ]))
    story.append(footer_table)
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph('Data Emissão: 21/06/2025', styles['RightAlign']))

    # Gera o PDF
    doc.build(story)
    print("PDF 'relatorio_engesep.pdf' gerado com sucesso!")

# Executa a função para gerar o PDF
# generate_report_pdf()

if __name__ == "__main__":
    # dfs = {
    #     'energia': {
    #         'values': pd.DataFrame({'data_hora': ['2025-01-01', '2025-01-02', '2025-01-03'], 'energia': [100, 200, 300]}),
    #         'statistics': {'energia': [100, 200, 300]}
    #     }
    # }
    # pdf = PDF(info, dfs)
    # pdf.output('teste.pdf')
    generate_report_pdf()
    # webbrowser.open('teste.pdf')






































