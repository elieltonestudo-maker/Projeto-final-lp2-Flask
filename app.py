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

            paises_compostos = ["Papua Nova Guiné", "Ilhas Salomão", "Reino Unido", "Nova Zelândia", "África do Sul", "Coreia do Sul", "Coreia do Norte", "Costa Rica", "El Salvador", "Estados Unidos", "Transnistria"]
            lixos_qualquer_lugar = ["Rara", "Polimero", "Polímero", "Estrangeira", "Edição", "Comemorativa"]

            i = 0
            while i < len(linhas):
                linha = linhas[i]
                
                if any(palavra in linha.lower() for palavra in ['sedex', 'frete', 'total', 'desconto', 'pago', 'pendente', 'dados bancários', 'pix:', 'banco']):
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
                        # 1. Limpa o início
                        descricao = re.sub(r'^Cédula\s+(Estrangeira|da|do|de|dos|das)?\s*-\s*', '', descricao_completa, flags=re.IGNORECASE).strip()
                        descricao = re.sub(r'^Cédula\s+(Estrangeira|da|do|de|dos|das)\s+', '', descricao, flags=re.IGNORECASE).strip()
                        
                        # Remove artigos soltos que sobraram (ex: "dos Comores" -> "Comores")
                        descricao = re.sub(r'^(dos|das|do|da|de)\s+', '', descricao, flags=re.IGNORECASE).strip()
                        
                        # 2. Remove parênteses
                        descricao = re.sub(r'\(.*?\)', '', descricao).strip()
                        
                        # 3. EXTRAI O ANO PRIMEIRO (Para o 2025 não ser confundido com valor facial)
                        ano = ""
                        match_ano = re.search(r'\b(19|20)\d{2}\b', descricao)
                        if match_ano:
                            ano = match_ano.group(0)
                            descricao = descricao.replace(match_ano.group(0), '').strip()
                        
                        # 4. Extrai o PICK
                        pick = ""
                        match_pick = re.search(r'\bP-?\s*\d+[a-z]*\b', descricao, re.IGNORECASE)
                        if match_pick:
                            pick = match_pick.group(0).upper()
                            descricao = descricao.replace(match_pick.group(0), '').strip()
                        
                        # 5. Extrai o ESTADO
                        estado = traduzir_estado(descricao) or "R"
                        for sigla, variacoes in ESTADOS_CONSERVACAO.items():
                            for v in variacoes:
                                descricao = re.sub(rf'\b{re.escape(v)}\b', '', descricao, flags=re.IGNORECASE)
                        
                        # 6. LIMPEZA FINAL DA DESCRIÇÃO
                        descricao = descricao.replace('-', ' ').strip()
                        descricao = re.sub(r'\s+', ' ', descricao).strip()
                        
                        # Separa País e Descrição
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

                        # Remove lixos de qualquer lugar
                        for lixo in lixos_qualquer_lugar:
                            descricao_final = re.sub(rf'\b{lixo}\b', '', descricao_final, flags=re.IGNORECASE).strip()

                        # Remove a última palavra se for curta (Sob, Ec, etc)
                        palavras_desc = descricao_final.split()
                        if palavras_desc:
                            ultima_palavra = palavras_desc[-1]
                            if len(ultima_palavra) <= 3 or '/' in ultima_palavra:
                                palavras_desc.pop()

                        descricao_final = ' '.join(palavras_desc).strip()
                        descricao_final = re.sub(r'\s+', ' ', descricao_final).strip()

                        cedulas_extraidas.append({
                            'codigo': lote,
                            'pais': pais,
                            'descricao': descricao_final,
                            'ano': ano,
                            'estado': estado,
                            'pick': pick,
                            'quantidade': 1,
                            'valor': valor,
                            'data': data_compra
                        })
                        
                        i += 3
                        continue
                
                i += 1

            return jsonify({'cedulas': cedulas_extraidas})
        except Exception as e:
            return jsonify({'erro': f'Erro ao ler o texto: {str(e)}'}), 500
        
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
                    catalogo=cedula_data.get('codigo', ''), # O Pick
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

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)