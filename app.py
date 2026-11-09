from flask import Flask, render_template, request, jsonify, Response
import re
import webbrowser     
import threading      
from models import db, Vendedor, Lote, Cedula
from dicionario import traduzir_estado, ESTADOS_CONSERVACAO
from services.pdf_processor import ProcessadorPDF
from services.exportadores import ExportadorDados
from services.text_processor import ProcessadorTexto
from services.lote_service import LoteService
from services.sistema_service import SistemaService


# --- FÁBRICA DA APLICAÇÃO FLASK ---
def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cedulas.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    @app.route('/')
    def index():
        return render_template('index.html')

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
        nome = dados.get('nome', '').strip()
        
        if not nome:
            return jsonify({'erro': 'Nome não informado'}), 400
            
        try:
            existente = Vendedor.query.filter_by(nome=nome).first()
            if existente:
                return jsonify({'mensagem': 'Vendedor já cadastrado!', 'id': existente.id}), 200
                
            novo_vendedor = Vendedor(nome=nome)
            db.session.add(novo_vendedor)
            db.session.commit()
            return jsonify({'mensagem': 'Vendedor cadastrado!', 'id': novo_vendedor.id}), 201
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
        try:
            # 1. Busca os dados no banco (usando a mesma query da pesquisa)
            resultados = db.session.query(
                Cedula.id, Cedula.pais, Cedula.valor_facial, Cedula.ano, 
                Cedula.catalogo, Cedula.estado, Cedula.quantidade, 
                Cedula.martelo, Cedula.data_compra, Vendedor.nome
            ).join(Lote, Cedula.lote_id == Lote.id)\
             .join(Vendedor, Lote.vendedor_id == Vendedor.id)\
             .order_by(Cedula.id.desc()).all()

            # 2. Formata os dados para o formato que a classe espera
            lista_dados = []
            for r in resultados:
                lista_dados.append({
                    'id': r.id, 
                    'pais': r.pais, 
                    'descricao': f"{r.valor_facial} {r.ano}".strip(),
                    'ano': r.ano, 
                    'catalogo': r.catalogo, 
                    'estado': r.estado, 
                    'quantidade': r.quantidade,
                    'martelo': r.martelo, 
                    'data': r.data_compra, 
                    'vendedor': r.nome
                })

            # 3. Instancia a classe Exportadora
            exportador = ExportadorDados(lista_dados)

            # 4. Retorna o arquivo no formato escolhido
            if formato == 'csv':
                return Response(exportador.para_csv(), mimetype='text/csv', 
                                headers={"Content-Disposition": "attachment;filename=relatorio_cedulas.csv"})
            elif formato == 'json':
                return Response(exportador.para_json(), mimetype='application/json')
            elif formato == 'txt':
                return Response(exportador.para_txt(), mimetype='text/plain')
            else:
                return jsonify({'erro': 'Formato não suportado. Use csv, json ou txt.'}), 400
                
        except Exception as e:
            return jsonify({'erro': str(e)}), 500    
        
    @app.route('/api/excluir_lote/<int:lote_id>', methods=['DELETE'])
    def api_excluir_lote(lote_id):
        try:
            lote = Lote.query.get(lote_id)
            if not lote:
                return jsonify({'erro': 'Lote não encontrado'}), 404
            
            db.session.delete(lote)
            db.session.commit()
            
            return jsonify({'mensagem': 'Lote excluído com sucesso!'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500
        
    @app.route('/api/excluir_cedula/<int:cedula_id>', methods=['DELETE'])
    def api_excluir_cedula(cedula_id):
        try:
            cedula = Cedula.query.get(cedula_id)
            if not cedula:
                return jsonify({'erro': 'Cédula não encontrada'}), 404
            
            db.session.delete(cedula)
            db.session.commit()
            
            return jsonify({'mensagem': 'Cédula excluída com sucesso!'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500
         
    
    @app.route('/api/backup')
    def api_backup():
        return SistemaService.gerar_backup(app)

    @app.route('/api/atualizar_bandeiras', methods=['POST'])
    def api_atualizar_bandeiras():
        resultado, status = SistemaService.atualizar_bandeiras()
        return jsonify(resultado), status
   
    return app   


import webbrowser
import threading

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