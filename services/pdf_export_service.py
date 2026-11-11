import io
import os
import urllib.request
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from PyPDF2 import PdfReader, PdfWriter

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.ticker import MaxNLocator
from PIL import Image as PILImage

class PDFExportService:
    
    MAPA_ISO = {
        "Brasil": "br", "Estados Unidos": "us", "Reino Unido": "gb", "Alemanha": "de",
        "França": "fr", "Itália": "it", "Japão": "jp", "China": "cn", "Argentina": "ar",
        "Portugal": "pt", "Espanha": "es", "México": "mx", "Canadá": "ca", "Rússia": "ru",
        "Índia": "in", "Austrália": "au", "África do Sul": "za", "Egito": "eg", "Nigéria": "ng",
        "Quênia": "ke", "Uganda": "ug", "Líbia": "ly", "Noruega": "no", "Suécia": "se",
        "Suíça": "ch", "Áustria": "at", "Bélgica": "be", "Holanda": "nl", "Polônia": "pl",
        "Hungria": "hu", "Romênia": "ro", "Bulgária": "bg", "Grécia": "gr", "Turquia": "tr",
        "Coreia do Sul": "kr", "Coreia do Norte": "kp", "Indonésia": "id", "Malásia": "my",
        "Filipinas": "ph", "Tailândia": "th", "Vietnã": "vn", "Singapura": "sg", "Nova Zelândia": "nz",
        "Chile": "cl", "Colômbia": "co", "Peru": "pe", "Venezuela": "ve", "Uruguai": "uy",
        "Paraguai": "py", "Bolívia": "bo", "Equador": "ec", "Costa Rica": "cr", "Cuba": "cu",
        "Guatemala": "gt", "Honduras": "hn", "El Salvador": "sv", "Nicarágua": "ni", "Panamá": "pa",
        "República Dominicana": "do", "Haiti": "ht", "Jamaica": "jm", "Afeganistão": "af",
        "Paquistão": "pk", "Bangladesh": "bd", "Sri Lanka": "lk", "Nepal": "np", "Butão": "bt",
        "Mianmar": "mm", "Camboja": "kh", "Laos": "la", "Mongólia": "mn", "Cazaquistão": "kz",
        "Uzbequistão": "uz", "Turcomenistão": "tm", "Tajiquistão": "tj", "Quirguistão": "kg",
        "Azerbaijão": "az", "Armênia": "am", "Geórgia": "ge", "Ucrânia": "ua", "Bielorrússia": "by",
        "Lituânia": "lt", "Letônia": "lv", "Estônia": "ee", "Finlândia": "fi", "Dinamarca": "dk",
        "Irlanda": "ie", "Islândia": "is", "Israel": "il", "Arábia Saudita": "sa", "Emirados Árabes Unidos": "ae",
        "Catar": "qa", "Kuwait": "kw", "Bahrein": "bh", "Omã": "om", "Iêmen": "ye", "Jordânia": "jo",
        "Líbano": "lb", "Síria": "sy", "Iraque": "iq", "Irã": "ir", "Chipre": "cy", "Malta": "mt",
        "Ilhas Salomão": "sb", "Papua Nova Guiné": "pg", "Fiji": "fj", "Samoa": "ws", "Tonga": "to",
        "Vanuatu": "vu", "Micronésia": "fm", "Palau": "pw", "Marshall": "mh", "Nauru": "nr",
        "Kiribati": "ki", "Tuvalu": "tv", "Transnistria": "md", "Tchecoslováquia": "cz",
        "Iugoslávia": "rs", "Sérvia": "rs", "Croácia": "hr", "Eslovênia": "si", "Bósnia": "ba",
        "Macedônia": "mk", "Montenegro": "me", "Kosovo": "xk", "Albânia": "al", "Eslováquia": "sk",
        "Chéquia": "cz", "República Tcheca": "cz", "Angola": "ao", "Moçambique": "mz",
        "Cabo Verde": "cv", "Guiné-Bissau": "gw", "São Tomé e Príncipe": "st", "Timor-Leste": "tl",
        "Serra Leoa": "sl", "Libéria": "lr", "Costa do Marfim": "ci", "Gana": "gh", "Togo": "tg",
        "Benin": "bj", "Camarões": "cm", "República Centro-Africana": "cf", "Chade": "td",
        "Congo": "cg", "República Democrática do Congo": "cd", "Gabão": "ga", "Guiné Equatorial": "gq",
        "Ruanda": "rw", "Burundi": "bi", "Etiópia": "et", "Eritreia": "er", "Djibuti": "dj",
        "Somália": "so", "Sudão": "sd", "Sudão do Sul": "ss", "Tanzânia": "tz", "Malaui": "mw",
        "Zâmbia": "zm", "Zimbábue": "zw", "Botsuana": "bw", "Namíbia": "na", "Lesoto": "ls",
        "Essuatíni": "sz", "Madagascar": "mg", "Maurício": "mu", "Seicheles": "sc", "Comores": "km",
        "Mauritânia": "mr", "Mali": "ml", "Níger": "ne", "Burkina Faso": "bf", "Senegal": "sn",
        "Gâmbia": "gm", "Guiné": "gn", "Argélia": "dz", "Marrocos": "ma", "Tunísia": "tn",
        "Escócia": "gb-sct", "Inglaterra": "gb-eng", "País de Gales": "gb-wls", "Irlanda do Norte": "gb-nir"
    }

    @staticmethod
    def _baixar_bandeira(pais):
        iso = PDFExportService.MAPA_ISO.get(pais, "un")
        url = f"https://flagcdn.com/w40/{iso}.png"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as response:
                img = PILImage.open(io.BytesIO(response.read()))
                img = img.convert("RGBA")
                fundo = PILImage.new("RGB", img.size, (255, 255, 255))
                fundo.paste(img, mask=img.split()[3])
                return fundo
        except Exception:
            return None

    @staticmethod
    def gerar_relatorio(cedulas, incluir_grafico=True, incluir_lista=True, incluir_total=True):
        buffer = io.BytesIO()
        
        # 1. CONFIGURAÇÃO DA PÁGINA (Margem inferior maior para o rodapé)
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4, 
            rightMargin=30, leftMargin=30, topMargin=40, bottomMargin=80 
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        titulo_style = ParagraphStyle('Titulo', parent=styles['Heading1'], textColor=colors.HexColor('#f1c40f'), spaceAfter=20)
        subtitulo_style = ParagraphStyle('Subtitulo', parent=styles['Heading2'], textColor=colors.HexColor('#1e1e1e'), spaceBefore=10, spaceAfter=10)
        cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=8, leading=10)
        header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor('#f1c40f'), fontName='Helvetica-Bold')
        
        elements.append(Paragraph("Gestão Numismática - Relatório de Acervo", titulo_style))
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 0.4 * inch))

        # 2. GRÁFICO
        if incluir_grafico:
            # Título da seção do gráfico
            elements.append(Paragraph("<b>Resumo por País</b>", subtitulo_style))
            elements.append(Spacer(1, 0.1 * inch))

            dados_paises = {}
            for c in cedulas:
                pais = c.get('pais', 'Desconhecido')
                dados_paises[pais] = dados_paises.get(pais, 0) + 1

            paises_ordenados = sorted(dados_paises.items(), key=lambda x: x[1], reverse=True)[:10]
            nomes = [p[0] for p in paises_ordenados]
            valores = [p[1] for p in paises_ordenados]

            fig, ax = plt.subplots(figsize=(8, 4))
            y_positions = range(len(nomes))
            
            ax.barh(y_positions, valores[::-1], color='#f1c40f', height=0.3)
            ax.set_xlabel('Quantidade de Cédulas')
            ax.set_title('Top 10 Países no Acervo')
            ax.set_yticks(y_positions)
            ax.set_yticklabels(nomes[::-1], fontsize=9, fontweight='bold')
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))
            ax.set_xlim(0, max(valores) + 1)

            for y, nome in zip(y_positions, nomes[::-1]):
                img_pil = PDFExportService._baixar_bandeira(nome)
                if img_pil:
                    imagebox = OffsetImage(img_pil, zoom=0.45) 
                    ab = AnnotationBbox(imagebox, (-0.38, y), xycoords=ax.get_yaxis_transform(), box_alignment=(1, 0.5), frameon=False)
                    ax.add_artist(ab)

            plt.subplots_adjust(left=0.45)
            
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='PNG', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            plt.close(fig)

            elements.append(Image(img_buffer, width=7*inch, height=3.2*inch))
            elements.append(Spacer(1, 0.4 * inch))

        # 3. TABELA DE CÉDULAS
        total_geral = 0.0
        for c in cedulas:
            total_geral += c.get('custo_final', 0)

        if incluir_lista:
            # Título da seção da tabela
            elements.append(Paragraph("<b>Cédulas Cadastradas</b>", subtitulo_style))
            elements.append(Spacer(1, 0.1 * inch))

            dados_tabela = [[
                Paragraph('País', header_style), Paragraph('Descrição', header_style), Paragraph('Ano', header_style), 
                Paragraph('Estado', header_style), Paragraph('Qtd', header_style), Paragraph('Custo Final', header_style)
            ]]
            
            for c in cedulas:
                dados_tabela.append([
                    Paragraph(c.get('pais', ''), cell_style), Paragraph(c.get('descricao', ''), cell_style),
                    Paragraph(c.get('ano', ''), cell_style), Paragraph(c.get('estado', ''), cell_style),
                    Paragraph(str(c.get('quantidade', 1)), cell_style), Paragraph(f"R&#36; {c.get('custo_final', 0):.2f}", cell_style)
                ])
                
            table = Table(dados_tabela, colWidths=[1.0*inch, 2.8*inch, 0.6*inch, 0.6*inch, 0.4*inch, 1.0*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e1e1e')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f9f9f9')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ALIGN', (5, 1), (5, -1), 'RIGHT'),
                ('REPEATROWS', (0, 0), (-1, 0)), # Repete o cabeçalho nas quebras de página
            ]))
            elements.append(table)
            elements.append(Spacer(1, 0.3 * inch))
        
        # 4. TOTAL GERAL
        if incluir_total:
            texto_total = f"<b>TOTAL GERAL DO ACERVO: R&#36; {total_geral:.2f}</b>"
            elements.append(Paragraph(texto_total, titulo_style))
        
        # Gera o PDF (Conteúdo)
        doc.build(elements)
        
        # 5. CARIMBO DO RODAPÉ (Logo + Texto + Numeração)
        buffer.seek(0)
        pdf_reader = PdfReader(buffer)
        pdf_writer = PdfWriter()

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        caminho_logo = os.path.join(base_dir, 'static', 'img', 'logo.png')

        for i, page in enumerate(pdf_reader.pages):
            footer_buffer = io.BytesIO()
            footer_canvas = canvas.Canvas(footer_buffer, pagesize=A4)
            
            # Desenha a linha dourada
            footer_canvas.setStrokeColor(colors.HexColor('#f1c40f'))
            footer_canvas.setLineWidth(1)
            footer_canvas.line(30, 40, A4[0] - 30, 40)
            
            # Desenha o logo
            if os.path.exists(caminho_logo):
                footer_canvas.setFillAlpha(0.3)
                footer_canvas.drawImage(caminho_logo, 30, 45, width=60, height=35, mask='auto')
                footer_canvas.setFillAlpha(1)
            
            # Desenha o texto
            footer_canvas.setFont('Helvetica-Bold', 10)
            footer_canvas.setFillColor(colors.HexColor('#1e1e1e'))
            footer_canvas.drawString(100, 55, "Gestão Numismática")
            
            footer_canvas.setFont('Helvetica', 8)
            footer_canvas.setFillColor(colors.grey)
            footer_canvas.drawString(100, 45, "Controle de Cédulas e Acervo")
            
            # Desenha a numeração
            footer_canvas.setFont('Helvetica', 9)
            footer_canvas.setFillColor(colors.grey)
            footer_canvas.drawRightString(A4[0] - 30, 55, f"Página {i+1} de {len(pdf_reader.pages)}")
            
            footer_canvas.save()
            footer_buffer.seek(0)
            
            footer_reader = PdfReader(footer_buffer)
            page.merge_page(footer_reader.pages[0])
            
            pdf_writer.add_page(page)

        final_buffer = io.BytesIO()
        pdf_writer.write(final_buffer)
        final_buffer.seek(0)
        
        return final_buffer