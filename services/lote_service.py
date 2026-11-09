from models import db, Vendedor, Lote, Cedula

class LoteService:
    @staticmethod
    def salvar(dados):
        if not dados:
            return {'erro': 'Nenhum dado recebido'}, 400

        try:
            nome_vendedor = dados.get('vendedor', 'Vendedor Desconhecido')
            vendedor = Vendedor.query.filter_by(nome=nome_vendedor).first()
            if not vendedor:
                vendedor = Vendedor(nome=nome_vendedor)
                db.session.add(vendedor)
                db.session.flush()

            # --- TRAVA DE SEGURANÇA (COMPARAÇÃO ITEM POR ITEM) ---
            ref_lote_para_verificar = ""
            if dados.get('cedulas') and len(dados['cedulas']) > 0:
                ref_lote_para_verificar = dados['cedulas'][0].get('ref_lote', '')
            
            # Gera uma "assinatura digital" do lote que está sendo salvo
            # Exemplo: "REF_12|BRASIL-10-1994-1|BRASIL-20-1994-1"
            assinatura_novo_lote = f"REF_{ref_lote_para_verificar}|"
            for c in sorted(dados.get('cedulas', []), key=lambda x: (x.get('pais',''), x.get('descricao',''))):
                assinatura_novo_lote += f"{c.get('pais')}-{c.get('descricao')}-{c.get('ano')}-{c.get('quantidade')}|"
            
            # Busca todos os lotes desse vendedor e gera a assinatura deles para comparar
            lotes_existentes = Lote.query.filter_by(vendedor_id=vendedor.id)\
                .join(Cedula).all()
            
            for lote_ex in lotes_existentes:
                # Pega a Ref. Lote do lote existente
                ref_ex = lote_ex.cedulas[0].ref_lote if lote_ex.cedulas else ""
                
                assinatura_lote_ex = f"REF_{ref_ex}|"
                # Precisamos ordenar as cédulas do lote existente da mesma forma
                cedulas_ex_ordenadas = sorted(lote_ex.cedulas, key=lambda x: (x.pais, x.valor_facial))
                for c in cedulas_ex_ordenadas:
                    assinatura_lote_ex += f"{c.pais}-{c.valor_facial}-{c.ano}-{c.quantidade}|"
                
                # Se as assinaturas baterem (mesma Ref e exatamente as mesmas cédulas e quantidades)
                if assinatura_novo_lote == assinatura_lote_ex:
                    return {'erro': f'⚠️ Lote duplicado! A Ref: {ref_lote_para_verificar} com estas cédulas e quantidades já foi cadastrada para {nome_vendedor}!'}, 400
            # ---------------------------------------------
            # ---------------------------------------------
            # --- CRIAÇÃO DO LOTE ---
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
            return {'mensagem': 'Lote salvo com sucesso!'}, 200

        except Exception as e:
            db.session.rollback()
            return {'erro': str(e)}, 500