from flask import Flask, render_template, request, jsonify
import pdfplumber
import re
from models import db, Vendedor, Lote, Cedula

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
        return self.texto_completo

    def extrair_cedulas(self):
        linhas = self.texto_completo.split('\n')
        cedulas_extraidas = []
        estados_validos = ["FE", "S/FE", "S", "MBC/S", "MBC", "BC/MBC", "BC", "R", "UTG"]

        i = 0
        while i < len(linhas):
            linha = linhas[i].strip()
            
            match = re.match(r'^(\d{4,5})\s*-\s*(.*)', linha)
            
            if match:
                lote = match.group(1)
                texto_bloco = match.group(2).strip()
                
                if (i + 1) < len(linhas):
                    texto_bloco += " " + linhas[i+1].strip()

                # Valor Total
                match_valor = re.search(r'R\$\s*([\d,]+)', texto_bloco)
                valor = float(match_valor.group(1).replace(',', '.')) if match_valor else 0.0
                if match_valor: 
                    texto_bloco = texto_bloco.replace(match_valor.group(0), '')

                # País
                match_pais = re.match(r'^([A-Za-zÀ-ÿ\s]+?)(?:\s*-|\s*\d)', texto_bloco)
                if match_pais:
                    pais = match_pais.group(1).strip()
                    texto_bloco = texto_bloco.replace(pais, '', 1).strip()
                else:
                    pais = "Desconhecido"

                # Estado
                estado_encontrado = "FE"
                for est in estados_validos:
                    if re.search(rf'\b{est}\b', texto_bloco):
                        estado_encontrado = est
                        texto_bloco = re.sub(rf'\b{est}\b', '', texto_bloco)
                        break

                # Pick
                pick = ""
                match_pick = re.search(r'\b[Pp]-?\s*(\d+)\b', texto_bloco)
                if match_pick:
                    pick = f"P-{match_pick.group(1)}"
                    texto_bloco = texto_bloco.replace(match_pick.group(0), '')

                # Ano
                ano = ""
                match_ano = re.search(r'\b((?:19|20)\d{2}(?:\s*-\s*(?:19|20)\d{2})?)\b', texto_bloco)
                if match_ano:
                    ano = match_ano.group(1).replace(' ', '')
                    texto_bloco = texto_bloco.replace(match_ano.group(0), '')

                # Quantidade e Descrição
                texto_bloco = texto_bloco.replace('polímero', '').replace('polimero', '').replace('soberba', '')
                texto_bloco = texto_bloco.replace('R$', '').replace('$', '').replace('(', '').replace(')', '')

                quantidade = 1
                match_qtd = re.search(r'\b(\d+)\s*$', texto_bloco.strip())
                if match_qtd:
                    num_achado = int(match_qtd.group(1))
                    if 1 <= num_achado <= 10:
                        quantidade = num_achado
                        texto_bloco = re.sub(rf'\b{match_qtd.group(1)}\s*$', '', texto_bloco.strip())

                palavras = texto_bloco.split()
                palavras_limpas = []
                for p in palavras:
                    if ',' in p or p == '-' or p in ['1', '2']:
                        continue
                    palavras_limpas.append(p)
                
                descricao_final = ' '.join(palavras_limpas[:3]).strip().title()

                cedulas_extraidas.append({
                    'codigo': lote,
                    'pais': pais,
                    'descricao': descricao_final,
                    'ano': ano,
                    'estado': estado_encontrado,
                    'pick': pick,
                    'quantidade': quantidade,
                    'valor': valor
                })
                
                i += 2
            else:
                i += 1

        return cedulas_extraidas # ESSA LINHA É CRUCIAL!
    
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
            # 1. Pega ou cria o vendedor
            nome_vendedor = dados.get('vendedor', 'Vendedor Desconhecido')
            vendedor = Vendedor.query.filter_by(nome=nome_vendedor).first()
            if not vendedor:
                vendedor = Vendedor(nome=nome_vendedor)
                db.session.add(vendedor)
                db.session.flush()

            # 2. Cria o Lote
            novo_lote = Lote(
                vendedor_id=vendedor.id,
                tipo=dados.get('tipo', 'Leilão Oficial'),
                frete=float(dados.get('frete', 0.0)),
                custos_extras=float(dados.get('custos_extras', 0.0))
            )
            db.session.add(novo_lote)
            db.session.flush()

            # 3. Salva as Cédulas
            for cedula_data in dados.get('cedulas', []):
                nova_cedula = Cedula(
                    lote_id=novo_lote.id,
                    pais=cedula_data.get('pais', ''),
                    valor_facial=cedula_data.get('descricao', ''),
                    ano=cedula_data.get('ano', ''), # <-- Salvando o ano
                    catalogo=cedula_data.get('codigo', ''),
                    estado=cedula_data.get('estado', 'FE'), # <-- Salvando o estado correto
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