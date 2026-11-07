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
        # Regex para capturar: Codigo - Pais - Descricao (Qtd) RS Valor
        padrao = r'(\d{4})\s*-\s*([A-Za-zÀ-ÿ\s]+)\s*-\s*([\d\sA-Za-zÀ-ÿ()\.\/-]+)\s*(\d)\s*R[S\$]\s*([\d,]+)'
        resultados = re.findall(padrao, self.texto_completo)
        
        cedulas_extraidas = []
        for res in resultados:
            codigo = res[0]
            pais = res[1].strip()
            descricao = res[2].strip()
            valor_str = res[4].replace(',', '.')
            valor = float(valor_str)
            
            cedulas_extraidas.append({
                'codigo': codigo,
                'pais': pais,
                'descricao': descricao,
                'valor': valor
            })
            
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

    # ROTA: Recebe o PDF e processa
    @app.route('/processar_pdf', methods=['POST'])
    def processar_pdf():
        if 'arquivo_pdf' not in request.files:
            return jsonify({'erro': 'Nenhum arquivo enviado'}), 400
        
        arquivo = request.files['arquivo_pdf']
        if arquivo.filename == '':
            return jsonify({'erro': 'Nenhum arquivo selecionado'}), 400

        processador = ProcessadorPDF(arquivo)
        processador.extrair_texto()
        cedulas = processador.extrair_cedulas()

        return jsonify({'cedulas': cedulas})

    # NOVA ROTA: Recebe os dados da tela e salva no banco SQLite
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
                db.session.flush() # Salva o vendedor para gerar o ID

            # 2. Cria o Lote
            novo_lote = Lote(
                vendedor_id=vendedor.id,
                tipo=dados.get('tipo', 'Leilão Oficial'),
                frete=float(dados.get('frete', 0.0)),
                custos_extras=float(dados.get('custos_extras', 0.0))
            )
            db.session.add(novo_lote)
            db.session.flush() # Salva o lote para gerar o ID

            # 3. Salva as Cédulas (Lendo a taxa individual que vem da tela)
            for cedula_data in dados.get('cedulas', []):
                nova_cedula = Cedula(
                    lote_id=novo_lote.id,
                    pais=cedula_data.get('pais', ''),
                    valor_facial=cedula_data.get('descricao', ''),
                    ano="", 
                    catalogo=cedula_data.get('codigo', ''),
                    estado="FE",
                    martelo=float(cedula_data.get('martelo', 0.0)),
                    taxa_leilao=float(cedula_data.get('taxa_linha', 0.0)) # <-- Pega a taxa da linha da tabela
                )
                db.session.add(nova_cedula)

            # Confirma tudo no banco de dados
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