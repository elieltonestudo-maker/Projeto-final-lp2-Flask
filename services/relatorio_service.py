from models import db, Vendedor, Lote, Cedula
from services.exportadores import ExportadorDados
from flask import Response

class RelatorioService:
    @staticmethod
    def exportar(formato):
        try:
            # 1. Busca os dados no banco
            resultados = db.session.query(
                Cedula.id, Cedula.pais, Cedula.valor_facial, Cedula.ano, 
                Cedula.catalogo, Cedula.estado, Cedula.quantidade, 
                Cedula.martelo, Cedula.data_compra, Vendedor.nome
            ).join(Lote, Cedula.lote_id == Lote.id)\
             .join(Vendedor, Lote.vendedor_id == Vendedor.id)\
             .order_by(Cedula.id.desc()).all()

            # 2. Formata os dados
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

            # 3. Instancia o exportador e retorna
            exportador = ExportadorDados(lista_dados)

            if formato == 'csv':
                return Response(exportador.para_csv(), mimetype='text/csv', 
                                headers={"Content-Disposition": "attachment;filename=relatorio_cedulas.csv"})
            elif formato == 'json':
                return Response(exportador.para_json(), mimetype='application/json')
            elif formato == 'txt':
                return Response(exportador.para_txt(), mimetype='text/plain')
            else:
                return {'erro': 'Formato não suportado. Use csv, json ou txt.'}, 400
                
        except Exception as e:
            return {'erro': str(e)}, 500