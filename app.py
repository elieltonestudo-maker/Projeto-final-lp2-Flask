from flask import Flask, render_template, request, jsonify, Response
import re
import os
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
from services.custo_service import CustoService
from models import db, Vendedor, Lote, Cedula, Usuario  
from flask import session, redirect, url_for  
from services.image_processor import ProcessadorImagem


# --- FÁBRICA DA APLICAÇÃO FLASK ---
def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cedulas.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
   
    # Faz a sessão expirar se o navegador for fechado
    app.config['SESSION_PERMANENT'] = False 
    # Impede que o navegador use cache nas rotas (forçando a checagem de login)
    app.config['SESSION_COOKIE_SECURE'] = False # Mude para True se for usar HTTPS
    app.config['SESSION_COOKIE_HTTPONLY'] = True # Impede acesso via JavaScript (segurança)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())
    db.init_app(app)
    
    @app.route('/')
    def index():
        # Pega o usuário logado para saber se é admin
        usuario_logado = Usuario.query.filter_by(username=session.get('usuario_nome')).first()
        is_admin = usuario_logado.is_admin if usuario_logado else False
        return render_template('index.html', is_admin=is_admin)

    # 👇 BLOCO DE LOGIN E LOGOUT AQUI 👇
    @app.before_request
    def require_login():
        # Adicionado 'cadastro' na lista
        rotas_livres = ['login', 'cadastro', 'static'] 
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
            username = request.form.get('username')
            senha = request.form.get('senha')
            
            if AuthService.verificar_login(username, senha):
                return redirect(url_for('index'))
            else:
                return render_template('login.html', erro='Usuário ou senha incorretos.')
                
        return render_template('login.html')

    @app.route('/cadastro', methods=['GET', 'POST'])
    def cadastro():
        if AuthService.esta_logado():
            return redirect(url_for('index'))
            
        if request.method == 'POST':
            username = request.form.get('username')
            senha = request.form.get('senha')
            confirmar = request.form.get('confirmar_senha')
            
            resultado, status = AuthService.cadastrar(username, senha, confirmar)
            if status == 201:
                return redirect(url_for('login'))
            else:
                return render_template('cadastro.html', erro=resultado['erro'])
                
        return render_template('cadastro.html')  

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
    
    
    @app.route('/processar_arquivo_drop', methods=['POST'])
    def processar_arquivo_drop():
        if 'arquivo' not in request.files:
            return jsonify({'erro': 'Nenhum arquivo enviado'}), 400
        
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            return jsonify({'erro': 'Arquivo sem nome'}), 400

        extensao = arquivo.filename.rsplit('.', 1)[-1].lower()

        try:
            if extensao == 'pdf':
                processador = ProcessadorPDF(arquivo)
                processador.extrair_texto()
                cedulas = processador.extrair_cedulas()
                return jsonify({'cedulas': cedulas, 'tipo': 'pdf'}), 200

            elif extensao in ['png', 'jpg', 'jpeg']:
                processador_img = ProcessadorImagem(arquivo)
                texto_bruto = processador_img.extrair_texto()
                processador_txt = ProcessadorTexto(texto_bruto)
                cedulas = processador_txt.extrair_cedulas()
                
                # 👇 Se não achou nenhuma cédula, retorna 200 mas com a lista vazia e o texto bruto
                # Isso permite que o JS mostre o texto no console para você debugar
                return jsonify({
                    'cedulas': cedulas, 
                    'tipo': 'imagem', 
                    'texto_bruto': texto_bruto
                }), 200
            elif extensao == 'txt':
                texto = arquivo.read().decode('utf-8')
                return jsonify({'texto': texto, 'tipo': 'txt'}), 200

            else:
                return jsonify({'erro': 'Formato não suportado. Envie PDF, Imagem ou TXT.'}), 400

        except Exception as e:
            return jsonify({'erro': f'Erro ao processar arquivo: {str(e)}'}), 500    
    
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

    @app.route('/api/usuarios', methods=['GET'])
    def api_usuarios():
        # Lista todos os usuários (incluindo a flag is_admin)
        usuarios = Usuario.query.order_by(Usuario.username).all()
        return jsonify({'usuarios': [
            {'id': u.id, 'username': u.username, 'is_admin': u.is_admin} 
            for u in usuarios
        ]})

    @app.route('/api/excluir_usuario/<int:usuario_id>', methods=['DELETE'])
    def api_excluir_usuario(usuario_id):
        # 1. Verifica se quem está pedindo a exclusão é o Administrador
        usuario_logado = Usuario.query.filter_by(username=session.get('usuario_nome')).first()
        if not usuario_logado or not usuario_logado.is_admin:
            return jsonify({'erro': 'Acesso negado. Apenas administradores podem excluir usuários.'}), 403

        # 2. Busca o usuário que se deseja excluir
        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado.'}), 404
            
        # 3. Impede que o admin exclua a si mesmo por acidente
        if usuario.username == session.get('usuario_nome'):
            return jsonify({'erro': 'Você não pode excluir o usuário que está logado.'}), 400
            
        try:
            db.session.delete(usuario)
            db.session.commit()
            return jsonify({'mensagem': 'Usuário excluído com sucesso!'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500
    
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

            # 1. Agrupa por lote_id e calcula o TOTAL DE SUBTOTAIS (Martelo + Taxa) de cada lote
            totais_subtotais_lotes = {}
            for r in resultados:
                if r.lote_id not in totais_subtotais_lotes:
                    totais_subtotais_lotes[r.lote_id] = 0
                
                # Calcula o subtotal da cédula (Martelo * Qtd + Taxa)
                valor_base = r.martelo * r.quantidade
                subtotal = valor_base + (valor_base * (r.taxa_leilao / 100))
                
                # Soma ao total do lote
                totais_subtotais_lotes[r.lote_id] += subtotal

            lista_cedulas = []
            for r in resultados:
                frete_total = r.frete + r.custos_extras
                total_subtotal_lote = totais_subtotais_lotes[r.lote_id]
                
                # 2. Chama o CustoService passando o TOTAL DE SUBTOTAIS
                custos = CustoService.calcular(
                    martelo=r.martelo,
                    quantidade=r.quantidade,
                    taxa_leilao=r.taxa_leilao,
                    frete_total=frete_total,
                    total_subtotal_lote=total_subtotal_lote
                )
                
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
                    'custo_base': custos['subtotal'],
                    'rateio': custos['rateio'],
                    'custo_final': custos['custo_final'],
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
        if formato == 'pdf':
            # Pega os parâmetros (padrão é True se não vier nada)
            incluir_grafico = request.args.get('grafico', 'true').lower() == 'true'
            incluir_lista = request.args.get('lista', 'true').lower() == 'true'
            incluir_total = request.args.get('total', 'true').lower() == 'true'
            
            resultado = RelatorioService.exportar(formato, incluir_grafico, incluir_lista, incluir_total)
        else:
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