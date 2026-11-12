from models import db, Vendedor, Lote, Cedula

class LoteService:
    
    @staticmethod
    def _gerar_assinatura(cedulas, ref):
        """Gera uma assinatura única para o lote, garantindo a mesma ordem de verificação."""
        partes = [f"REF_{ref}"]
        # Ordena por País, depois Descrição, depois Ano, para garantir consistência
        for c in sorted(cedulas, key=lambda x: (x.get('pais',''), x.get('valor_facial', x.get('descricao','')), x.get('ano',''))):
            partes.append(f"{c.get('pais')}|{c.get('valor_facial', c.get('descricao'))}|{c.get('ano')}|{c.get('quantidade',1)}")
        return "||".join(partes)

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

            # --- TRAVA DE SEGURANÇA (COMPARAÇÃO PADRONIZADA) ---
            ref_lote_para_verificar = ""
            if dados.get('cedulas') and len(dados['cedulas']) > 0:
                ref_lote_para_verificar = dados['cedulas'][0].get('ref_lote', '')
            
            # Gera a assinatura do lote NOVO que está chegando
            assinatura_novo_lote = LoteService._gerar_assinatura(dados.get('cedulas', []), ref_lote_para_verificar)
            
            # Busca todos os lotes desse vendedor
            lotes_existentes = Lote.query.filter_by(vendedor_id=vendedor.id).join(Cedula).all()
            
            for lote_ex in lotes_existentes:
                # Pega a Ref. Lote do lote existente no banco
                ref_ex = lote_ex.cedulas[0].ref_lote if lote_ex.cedulas else ""
                
                # Transforma as cédulas do banco em dicionários para usar a MESMA função de assinatura
                cedulas_existentes_dados = [
                    {
                        'pais': c.pais, 
                        'valor_facial': c.valor_facial, 
                        'ano': c.ano, 
                        'quantidade': c.quantidade
                    } for c in lote_ex.cedulas
                ]
                
                # Gera a assinatura do lote EXISTENTE
                assinatura_lote_ex = LoteService._gerar_assinatura(cedulas_existentes_dados, ref_ex)
                
                # Compara
                if assinatura_novo_lote == assinatura_lote_ex:
                    return {'erro': f'⚠️ Lote duplicado! A Ref: {ref_lote_para_verificar} com estas cédulas e quantidades já foi cadastrada para {nome_vendedor}!'}, 400
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