from flask import Flask, render_template, request, jsonify
import pdfplumber
import re
from models import db, Vendedor, Lote, Cedula
from dicionario import traduzir_estado, ESTADOS_CONSERVACAO

# --- CLASSE ORIENTADA A OBJETOS PARA PROCESSAR O PDF ---
class ProcessadorPDF:
    def __init__(self, arquivo_pdf):
        self.arquivo = arquivo_pdf
        self.texto_completo = ""

    def extrair_texto(self):
        with pdfplumber.open(self.arquivo) as pdf:
            for pagina in pdf.pages:
                texto = pagina.extract_text()
                if texto:
                    self.texto_completo += texto + "\n"
        
        # Salva o texto bruto para debug (opcional, mas ajuda)
        with open("debug_pdf.txt", "w", encoding="utf-8") as f:
            f.write(self.texto_completo)
        
        return self.texto_completo

    def extrair_cedulas(self):
        linhas = self.texto_completo.split('\n')
        cedulas_extraidas = []
        
        # Puxa a data global do topo
        data_compra_global = ""
        match_data = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', self.texto_completo)
        if match_data:
            data_compra_global = match_data.group(1)

        linhas = [l.strip() for l in linhas if l.strip()]

        i = 0
        while i < len(linhas):
            linha = linhas[i]
            
            # TRAVA DE SEGURANÇA: Ignora linhas de totais ou lixo
            if any(palavra in linha.lower() for palavra in ['totais', 'desconto', 'pago', 'pendente', 'total final']):
                i += 1
                continue

            match = re.match(r'^(\d{4,5})\s*-\s*(.*)', linha)
            
            if match:
                lote = match.group(1)
                texto_bloco = match.group(2).strip()
                
                # Junta com a linha de baixo
                if (i + 1) < len(linhas):
                    proxima_linha = linhas[i+1]
                    if not re.match(r'^\d{4,5}\s*-', proxima_linha):
                        texto_bloco += " " + proxima_linha
                        i += 1 
                
                # 1. ANO PRIMEIRO (A ordem importa!)
                ano = ""
                match_ano = re.search(r'\b(19|20)\d{2}(?:\s*-\s*(19|20)\d{2})?\b', texto_bloco)
                if match_ano:
                    ano = match_ano.group(0).replace(' ', '')
                    texto_bloco = texto_bloco.replace(match_ano.group(0), '')

                # 2. VALOR TOTAL (R$)
                match_valor = re.search(r'R\$\s*([\d,]+)', texto_bloco)
                if not match_valor:
                    i += 1
                    continue
                valor = float(match_valor.group(1).replace(',', '.'))
                texto_bloco = texto_bloco.replace(match_valor.group(0), '')

                # 3. PAÍS
                match_pais = re.match(r'^([A-Za-zÀ-ÿ\s]+?)(?:\s*-|\s*\d)', texto_bloco)
                if match_pais:
                    pais = match_pais.group(1).strip()
                    texto_bloco = texto_bloco.replace(pais, '', 1).strip()
                else:
                    pais = "Desconhecido"

                # 4. ESTADO
                estado = traduzir_estado(texto_bloco) or "R"
                for sigla, variacoes in ESTADOS_CONSERVACAO.items():
                    for v in variacoes:
                        texto_bloco = re.sub(rf'\b{re.escape(v)}\b', '', texto_bloco, flags=re.IGNORECASE)

                # 5. QUANTIDADE E DESCRIÇÃO
                texto_bloco = texto_bloco.replace('polímero', '').replace('polimero', '').replace('soberba', '')
                texto_bloco = re.sub(r'\d+,\d+', '', texto_bloco)
                texto_bloco = texto_bloco.replace('R$', '').replace('(', '').replace(')', '').replace('-', ' ').strip()
                
                palavras = texto_bloco.split()
                descricao_palavras = []
                quantidade = 1
                
                # Limpa palavras e acha a quantidade
                for p in palavras:
                    if p.isdigit() and 1 <= int(p) <= 9 and len(descricao_palavras) > 0:
                        quantidade = int(p)
                    elif p == '0':
                        continue
                    else:
                        descricao_palavras.append(p)
                
                descricao_final = ' '.join(descricao_palavras).strip().title()

                cedulas_extraidas.append({
                    'codigo': lote,
                    'pais': pais,
                    'descricao': descricao_final,
                    'ano': ano,
                    'estado': estado,
                    'pick': "",
                    'quantidade': quantidade,
                    'valor': valor,
                    'data': data_compra_global
                })
                
            i += 1 

        return cedulas_extraidas

# --- FÁBRICA DA APLICAÇÃO FLASK ---
def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cedulas.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/processar_pdf', methods=['POST'])
    def processar_pdf():
        if 'arquivo_pdf' not in request.files:
            return jsonify({'erro': 'Nenhum arquivo enviado'}), 400
        
        arquivo = request.files['arquivo_pdf']
        if arquivo.filename == '':
            return jsonify({'erro': 'Nenhum arquivo selecionado'}), 400

        try:
            processador = ProcessadorPDF(arquivo)
            processador.extrair_texto()
            cedulas = processador.extrair_cedulas()
            return jsonify({'cedulas': cedulas})
        except Exception as e:
            return jsonify({'erro': f'Erro ao ler o PDF: {str(e)}'}), 500

    @app.route('/salvar_lote', methods=['POST'])
    def salvar_lote():
        dados = request.get_json()
        
        if not dados:
            return jsonify({'erro': 'Nenhum dado recebido'}), 400
            
        try:
            nome_vendedor = dados.get('vendedor', 'Vendedor Desconhecido')
            vendedor = Vendedor.query.filter_by(nome=nome_vendedor).first()
            if not vendedor:
                vendedor = Vendedor(nome=nome_vendedor)
                db.session.add(vendedor)
                db.session.flush()

            novo_lote = Lote(
                vendedor_id=vendedor.id,
                tipo=dados.get('tipo', 'Leilão Oficial'),
                frete=float(dados.get('frete', 0.0)),
                custos_extras=float(dados.get('custos_extras', 0.0))
            )
            db.session.add(novo_lote)
            db.session.flush()

            for cedula_data in dados.get('cedulas', []):
                nova_cedula = Cedula(
                    lote_id=novo_lote.id,
                    pais=cedula_data.get('pais', ''),
                    valor_facial=cedula_data.get('descricao', ''),
                    ano=cedula_data.get('ano', ''),
                    catalogo=cedula_data.get('codigo', ''),
                    estado=cedula_data.get('estado', 'FE'),
                    martelo=float(cedula_data.get('martelo', 0.0)),
                    taxa_leilao=float(cedula_data.get('taxa_linha', 0.0))
                )
                db.session.add(nova_cedula)

            db.session.commit()
            return jsonify({'mensagem': 'Lote salvo com sucesso!'}), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)