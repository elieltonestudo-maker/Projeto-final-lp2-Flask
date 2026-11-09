from flask import Flask, render_template, request, jsonify, Response
import re
from models import db, Vendedor, Lote, Cedula
from dicionario import traduzir_estado, ESTADOS_CONSERVACAO
from services.pdf_processor import ProcessadorPDF
from services.exportadores import ExportadorDados


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
            cedulas_extraidas = []
            linhas = texto.split('\n')
            linhas = [l.strip() for l in linhas if l.strip()]

            data_compra = ""
            match_data = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', texto)
            if match_data:
                data_compra = match_data.group(1)

            paises_compostos = ["Papua Nova Guiné", "Ilhas Salomão", "Reino Unido", "Nova Zelândia", "África do Sul", "Coreia do Sul", "Coreia do Norte", "Costa Rica", "El Salvador", "Estados Unidos", "Transnistria", "Guatemala", "Nigéria", "Tchecoslováquia", "Serra Leoa", "Afeganistão", "Coréia do Sul", "Seychelles", "Hungria"]
            lixos_qualquer_lugar = ["Rara", "Polimero", "Polímero", "Estrangeira", "Edição", "Comemorativa", "Aniversário", "Universidade", "Dr.", "Escassa", "Muito", "Difícil", "Bastante", "Atrativa", "Estimativa", "Tipo", "Pick", "Flor de Estampa"]

            i = 0
            while i < len(linhas):
                linha = linhas[i]
                
                if any(palavra in linha.lower() for palavra in ['sedex', 'frete', 'total', 'desconto', 'pago', 'pendente', 'dados bancários', 'pix:', 'banco', 'pac', 'jadlog', 'mini envio']):
                    i += 1
                    continue
                
                match_lote = re.match(r'Lote:\s*(\d+)', linha, re.IGNORECASE)
                
                if match_lote:
                    lote = match_lote.group(1)
                    descricao_completa = ""
                    valor = 0.0
                    
                    if (i + 1) < len(linhas):
                        descricao_completa = linhas[i+1]
                    if (i + 2) < len(linhas):
                        linha_valor = linhas[i+2]
                        match_valor = re.search(r'R\$\s*([\d\.,]+)', linha_valor)
                        if match_valor:
                            valor_str = match_valor.group(1).replace(',', '.')
                            valor = float(valor_str)
                    
                    if descricao_completa and valor > 0:
                        descricao = re.sub(r'^\s*C[ÉE]DULA\s+(Estrangeira|da|do|de|dos|das)?\s*[-]?\s*', '', descricao_completa, flags=re.IGNORECASE).strip()
                        descricao = re.sub(r'^\s*C[ÉE]DULA\s+', '', descricao, flags=re.IGNORECASE).strip()
                        descricao = re.sub(r'^\s*(dos|das|do|da|de)\s+', '', descricao, flags=re.IGNORECASE).strip()
                        
                        descricao = re.sub(r'\(.*?\)', '', descricao).strip()
                        
                        anos_encontrados = re.findall(r'\b(?:19|20)\d{2}\b', descricao)
                        ano = ""
                        if anos_encontrados:
                            ano = anos_encontrados[-1]
                            descricao = descricao[::-1].replace(ano[::-1], '', 1)[::-1].strip()
                        
                        pick = ""
                        match_pick = re.search(r'\b(?:Pick|P[-#]?)\s*(\d+[a-z]*)\b', descricao, re.IGNORECASE)
                        if match_pick:
                            pick = match_pick.group(1).upper()
                            descricao = descricao.replace(match_pick.group(0), '').strip()
                        
                        estado = traduzir_estado(descricao) or "R"
                        for sigla, variacoes in ESTADOS_CONSERVACAO.items():
                            for v in variacoes:
                                descricao = re.sub(rf'\b{re.escape(v)}\b', '', descricao, flags=re.IGNORECASE)
                        
                        descricao = descricao.replace('-', ' ').replace('#', ' ').strip()
                        descricao = re.sub(r'\s+', ' ', descricao).strip()
                        
                        pais = "Desconhecido"
                        descricao_final = descricao.title()
                        
                        for pc in paises_compostos:
                            if descricao.lower().startswith(pc.lower()):
                                pais = pc
                                descricao_final = descricao[len(pc):].strip().title()
                                break
                        
                        if pais == "Desconhecido" and descricao.split():
                            partes = descricao.split()
                            pais = partes[0]
                            descricao_final = ' '.join(partes[1:]).strip().title()

                        for lixo in lixos_qualquer_lugar:
                            descricao_final = re.sub(rf'\b{lixo}\b', '', descricao_final, flags=re.IGNORECASE).strip()

                        palavras_desc = descricao_final.split()
                        if palavras_desc:
                            ultima_palavra = palavras_desc[-1]
                            if len(ultima_palavra) <= 3 or '/' in ultima_palavra:
                                palavras_desc.pop()

                        descricao_final = ' '.join(palavras_desc).strip()
                        descricao_final = re.sub(r'\s+', ' ', descricao_final).strip()

                        cedulas_extraidas.append({
                            'codigo': lote, 'pais': pais, 'descricao': descricao_final, 'ano': ano,
                            'estado': estado, 'pick': pick, 'quantidade': 1, 'valor': valor, 'data': data_compra
                        })
                        
                        i += 3
                        continue
                
                i += 1

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
        
        if not dados:
            return jsonify({'erro': 'Nenhum dado recebido'}), 400
            
        try:
            nome_vendedor = dados.get('vendedor', 'Vendedor Desconhecido')
            vendedor = Vendedor.query.filter_by(nome=nome_vendedor).first()
            if not vendedor:
                vendedor = Vendedor(nome=nome_vendedor)
                db.session.add(vendedor)
                db.session.flush()

            # --- TRAVA DE SEGURANÇA (ANTI-DUPLICIDADE) ---
            # Verifica se já existe um lote com o mesmo Vendedor, Data e Valor Total
            ref_lote_para_verificar = ""
            data_compra_para_verificar = ""
            
            if dados.get('cedulas') and len(dados['cedulas']) > 0:
                ref_lote_para_verificar = dados['cedulas'][0].get('ref_lote', '')
                data_compra_para_verificar = dados['cedulas'][0].get('data', '')
            
            # Verifica duplicidade por Ref. Lote (se preenchida)
            if ref_lote_para_verificar:
                lote_existente = Lote.query.filter_by(
                    vendedor_id=vendedor.id, 
                ).join(Cedula).filter(Cedula.ref_lote == ref_lote_para_verificar).first()

                if lote_existente:
                    return jsonify({'erro': f'⚠️ Este lote (Ref: {ref_lote_para_verificar}) já foi cadastrado para o vendedor {nome_vendedor}!'}), 400
            
            # Se não tiver Ref. Lote, verifica duplicidade por Data + Valor Total do Lote
            elif data_compra_para_verificar:

                total_cedulas_novo = sum(float(c.get('martelo', 0)) * int(c.get('quantidade', 1)) for c in dados['cedulas'])
                
                # Busca lotes do mesmo vendedor e mesma data
                lotes_existentes = Lote.query.filter_by(
                    vendedor_id=vendedor.id
                ).join(Cedula).filter(Cedula.data_compra == data_compra_para_verificar).all()
                
                for lote_ex in lotes_existentes:
                    total_cedulas_existente = sum(c.martelo * c.quantidade for c in lote_ex.cedulas)
                    if abs(total_cedulas_existente - total_cedulas_novo) < 0.01: # Compara valores
                        return jsonify({'erro': f'⚠️ Já existe um lote com este mesmo vendedor ({nome_vendedor}), data ({data_compra_para_verificar}) e valor total ({total_cedulas_novo:.2f})!'}), 400
            # ---------------------------------------------

            novo_lote = Lote(
                vendedor_id=vendedor.id,
                tipo=dados.get('tipo', 'Leilão Oficial'),
                origem=dados.get('origem', 'Leilão Oficial'),
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
                    estado=cedula_data.get('estado', 'R'),
                    quantidade=int(cedula_data.get('quantidade', 1)),
                    data_compra=cedula_data.get('data', ''),
                    ref_lote=cedula_data.get('ref_lote', ''),
                    martelo=float(cedula_data.get('martelo', 0.0)),
                    taxa_leilao=float(cedula_data.get('taxa_linha', 0.0))
                )
                db.session.add(nova_cedula)

            db.session.commit()
            return jsonify({'mensagem': 'Lote salvo com sucesso!'}), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500

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
    # 👆 FIM DA NOVA ROTA 👆

    return app   


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)