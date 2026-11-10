from flask import Flask, render_template, request, jsonify, Response
import re
import webbrowser     
import threading 
import shutil     
from models import db, Vendedor, Lote, Cedula
from dicionario import traduzir_estado, ESTADOS_CONSERVACAO
from services.pdf_processor import ProcessadorPDF
from services.exportadores import ExportadorDados
from services.text_processor import ProcessadorTexto
from services.lote_service import LoteService
from services.sistema_service import SistemaService
from services.relatorio_service import RelatorioService
from services.exclusao_service import ExclusaoService
from flask import session, redirect, url_for
from services.auth_service import AuthService
from services.vendedor_service import VendedorService



# --- FÁBRICA DA APLICAÇÃO FLASK ---
def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cedulas.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'uma-chave-super-secreta-para-sessoes-2' 
    db.init_app(app)

    @app.route('/')
    def index():
        return render_template('index.html')

    # 👇 BLOCO DE LOGIN E LOGOUT AQUI 👇
    @app.before_request
    def require_login():
        # Lista de rotas que NÃO precisam de login
        rotas_livres = ['login', 'static'] 
        if request.endpoint and not AuthService.esta_logado() and request.endpoint not in rotas_livres:
            return redirect(url_for('login'))

    @app.after_request
    def add_header(response):
        # Impede o navegador de fazer cache das páginas do sistema
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response       

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if AuthService.esta_logado():
            return redirect(url_for('index'))
            
        if request.method == 'POST':
            senha = request.form.get('senha')
            if AuthService.verificar_senha(senha):
                AuthService.fazer_login()
                return redirect(url_for('index'))
            else:
                return render_template('login.html', erro='Senha incorreta. Tente novamente.')
                
        return render_template('login.html')

    @app.route('/logout')
    def logout():
        AuthService.fazer_logout()
        # Cria a resposta de redirecionamento
        response = redirect(url_for('login'))
        # Força a limpeza do cookie de sessão no navegador
        response.delete_cookie('session')
        return response
    # 👆 FIM DO BLOCO DE LOGIN E LOGOUT 👆

    @app.route('/processar_texto', methods=['POST'])
    def processar_texto():
        dados = request.get_json()
        texto = dados.get('texto', '')
        
        if not texto:
            return jsonify({'erro': 'Nenhum texto recebido'}), 400

        try:
            processador = ProcessadorTexto(texto)
            cedulas_extraidas = processador.extrair_cedulas()
            return jsonify({'cedulas': cedulas_extraidas})
        except Exception as e:
            return jsonify({'erro': f'Erro ao ler o texto: {str(e)}'}), 500

   
   # 👇 COLE A ROTA DO PDF AQUI 👇
    @app.route('/processar_pdf', methods=['POST'])
    def processar_pdf():
        if 'arquivo_pdf' not in request.files:
            return jsonify({'erro': 'Nenhum arquivo enviado'}), 400
        arquivo = request.files['arquivo_pdf']
        if arquivo.filename == '':
            return jsonify({'erro': 'Arquivo sem nome'}), 400
        
        try:
            processador = ProcessadorPDF(arquivo)
            processador.extrair_texto()
            cedulas = processador.extrair_cedulas()
            return jsonify({'cedulas': cedulas}), 200
        except Exception as e:
            return jsonify({'erro': f'Erro ao processar PDF: {str(e)}'}), 500
    # 👆 FIM DA ROTA DO PDF 👆
    
    @app.route('/salvar_lote', methods=['POST'])
    def salvar_lote():
        dados = request.get_json()
        resultado, status = LoteService.salvar(dados)
        return jsonify(resultado), status

    # --- ROTAS DA API ---
    @app.route('/api/vendedores', methods=['GET'])
    def api_vendedores():
        try:
            vendedores = Vendedor.query.order_by(Vendedor.nome).all()
            lista = [{'id': v.id, 'nome': v.nome} for v in vendedores]
            return jsonify({'vendedores': lista})
        except Exception as e:
            return jsonify({'erro': str(e)}), 500

    @app.route('/api/adicionar_vendedor', methods=['POST'])
    def api_adicionar_vendedor():
        dados = request.get_json()
        resultado, status = VendedorService.adicionar(dados.get('nome', ''))
        return jsonify(resultado), status

    @app.route('/api/editar_vendedor/<int:vendedor_id>', methods=['PUT'])
    def api_editar_vendedor(vendedor_id):
        dados = request.get_json()
        resultado, status = VendedorService.editar(vendedor_id, dados.get('nome', ''))
        return jsonify(resultado), status

    @app.route('/api/excluir_vendedor/<int:vendedor_id>', methods=['DELETE'])
    def api_excluir_vendedor(vendedor_id):
        resultado, status = VendedorService.excluir(vendedor_id)
        return jsonify(resultado), status

    
    @app.route('/api/pesquisar', methods=['GET'])
    def api_pesquisar():
        try:
            resultados = db.session.query(
                Cedula.id, Cedula.lote_id, Cedula.pais, Cedula.valor_facial, Cedula.ano, 
                Cedula.catalogo, Cedula.estado, Cedula.quantidade, 
                Cedula.martelo, Cedula.taxa_leilao, Cedula.data_compra, 
                Cedula.ref_lote, Lote.origem, Lote.frete, Lote.custos_extras, Vendedor.nome
            ).join(Lote, Cedula.lote_id == Lote.id)\
             .join(Vendedor, Lote.vendedor_id == Vendedor.id)\
             .order_by(Cedula.id.desc()).all()

            # Precisamos do valor total de cada lote para fazer o rateio proporcional
            # Vamos agrupar por lote_id e calcular o total de martelos de cada um
            totais_lotes = {}
            for r in resultados:
                if r.lote_id not in totais_lotes:
                    totais_lotes[r.lote_id] = 0
                # O valor base do lote é martelo * quantidade
                totais_lotes[r.lote_id] += (r.martelo * r.quantidade)

            lista_cedulas = []
            for r in resultados:
                # Calcula o valor base da cédula (Martelo * Qtd + Taxa)
                valor_bruto = r.martelo * r.quantidade
                valor_base = valor_bruto + (valor_bruto * (r.taxa_leilao / 100))
                
                # Calcula o Rateio do Frete
                valor_total_frete_lote = r.frete + r.custos_extras
                total_martelos_lote = totais_lotes[r.lote_id]
                
                rateio = 0.0
                if total_martelos_lote > 0:
                    # (Valor base da cédula / Valor total do lote) * Frete Total
                    rateio = (valor_bruto / total_martelos_lote) * valor_total_frete_lote
                
                custo_final = valor_base + rateio
                
                lista_cedulas.append({
                    'id': r.id, 
                    'lote_id': r.lote_id,
                    'pais': r.pais, 
                    'ano': r.ano,
                    'descricao': f"{r.valor_facial} {r.ano}".strip(),
                    'catalogo': r.catalogo, 
                    'estado': r.estado, 
                    'quantidade': r.quantidade,
                    'martelo': r.martelo, 
                    'custo_base': valor_base,      # O valor sem frete
                    'rateio': rateio,              # O valor do frete rateado
                    'custo_final': custo_final,    # O valor real (base + frete)
                    'data': r.data_compra,
                    'ref_lote': r.ref_lote, 
                    'origem': r.origem, 
                    'vendedor': r.nome
                })
            
            return jsonify({'cedulas': lista_cedulas})
        except Exception as e:
            return jsonify({'erro': str(e)}), 500

    @app.route('/api/exportar/<formato>', methods=['GET'])
    def api_exportar(formato):
        resultado = RelatorioService.exportar(formato)
        if isinstance(resultado, tuple): 
            return jsonify(resultado[0]), resultado[1]
        return resultado 

    @app.route('/api/excluir_lote/<int:lote_id>', methods=['DELETE'])
    def api_excluir_lote(lote_id):
        resultado, status = ExclusaoService.excluir_lote(lote_id)
        return jsonify(resultado), status

    @app.route('/api/excluir_cedula/<int:cedula_id>', methods=['DELETE'])
    def api_excluir_cedula(cedula_id):
        resultado, status = ExclusaoService.excluir_cedula(cedula_id)
        return jsonify(resultado), status
         
    
    @app.route('/api/backup')
    def api_backup():
        return SistemaService.gerar_backup(app)

    @app.route('/api/restaurar_backup', methods=['POST'])
    def api_restaurar_backup():
        if 'arquivo_db' not in request.files:
            return jsonify({'erro': 'Nenhum arquivo enviado.'}), 400
        
        arquivo = request.files['arquivo_db']
        resultado, status = SistemaService.restaurar_backup(arquivo)
        return jsonify(resultado), status
    

    @app.route('/api/atualizar_bandeiras', methods=['POST'])
    def api_atualizar_bandeiras():
        resultado, status = SistemaService.atualizar_bandeiras()
        return jsonify(resultado), status
   
    return app   


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    
    # Função que abre o navegador após 1 segundo (para dar tempo do Flask subir)
    def abrir_navegador():
        webbrowser.open_new('http://127.0.0.1:5000/')

    # Dispara a abertura do navegador em uma thread separada
    threading.Timer(1, abrir_navegador).start()
    
    # Inicia o Flask
    app.run(debug=True, use_reloader=False)