from models import db, Lote, Cedula

class ExclusaoService:
    @staticmethod
    def excluir_lote(lote_id):
        try:
            lote = Lote.query.get(lote_id)
            if not lote:
                return {'erro': 'Lote não encontrado'}, 404
            
            db.session.delete(lote)
            db.session.commit()
            
            return {'mensagem': 'Lote excluído com sucesso!'}, 200
        except Exception as e:
            db.session.rollback()
            return {'erro': str(e)}, 500

    @staticmethod
    def excluir_cedula(cedula_id):
        try:
            cedula = Cedula.query.get(cedula_id)
            if not cedula:
                return {'erro': 'Cédula não encontrada'}, 404
            
            db.session.delete(cedula)
            db.session.commit()
            
            return {'mensagem': 'Cédula excluída com sucesso!'}, 200
        except Exception as e:
            db.session.rollback()
            return {'erro': str(e)}, 500