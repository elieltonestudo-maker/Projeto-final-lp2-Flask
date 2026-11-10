from models import db, Vendedor

class VendedorService:
    @staticmethod
    def adicionar(nome):
        nome = nome.strip()
        if not nome:
            return {'erro': 'Nome não informado'}, 400
            
        try:
            existente = Vendedor.query.filter_by(nome=nome).first()
            if existente:
                return {'mensagem': 'Vendedor já cadastrado!', 'id': existente.id}, 200
                
            novo_vendedor = Vendedor(nome=nome)
            db.session.add(novo_vendedor)
            db.session.commit()
            return {'mensagem': 'Vendedor cadastrado!', 'id': novo_vendedor.id}, 201
        except Exception as e:
            db.session.rollback()
            return {'erro': str(e)}, 500

    @staticmethod
    def editar(vendedor_id, novo_nome):
        novo_nome = novo_nome.strip()
        if not novo_nome:
            return {'erro': 'Nome não informado'}, 400
            
        try:
            vendedor = Vendedor.query.get(vendedor_id)
            if not vendedor:
                return {'erro': 'Vendedor não encontrado'}, 404
                
            # Verifica se já existe outro vendedor com o mesmo nome
            existente = Vendedor.query.filter(Vendedor.nome == novo_nome, Vendedor.id != vendedor_id).first()
            if existente:
                return {'erro': 'Já existe outro vendedor com este nome.'}, 400
                
            nome_antigo = vendedor.nome
            vendedor.nome = novo_nome
            db.session.commit()
            
            return {
                'mensagem': 'Vendedor atualizado com sucesso!', 
                'id': vendedor.id, 
                'nome': vendedor.nome,
                'nome_antigo': nome_antigo
            }, 200
        except Exception as e:
            db.session.rollback()
            return {'erro': str(e)}, 500

    @staticmethod
    def excluir(vendedor_id):
        try:
            vendedor = Vendedor.query.get(vendedor_id)
            if not vendedor:
                return {'erro': 'Vendedor não encontrado'}, 404
                
            # Regra de segurança: Não deixa excluir se tiver lotes
            if vendedor.lotes:
                return {'erro': 'Não é possível excluir. Este vendedor possui lotes cadastrados no sistema.'}, 400
                
            db.session.delete(vendedor)
            db.session.commit()
            return {'mensagem': 'Vendedor excluído com sucesso!'}, 200
        except Exception as e:
            db.session.rollback()
            return {'erro': str(e)}, 500