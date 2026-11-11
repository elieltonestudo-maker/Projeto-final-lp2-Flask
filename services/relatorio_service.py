from models import db, Vendedor, Lote, Cedula
from services.exportadores import ExportadorDados
from services.pdf_export_service import PDFExportService
from services.custo_service import CustoService
from flask import Response

class RelatorioService:
    @staticmethod
    def exportar(formato, incluir_grafico=True, incluir_lista=True, incluir_total=True): # 👈 Novos parâmetros
        try:
            # 1. Busca os dados no banco (incluindo os campos necessários para o cálculo)
            resultados = db.session.query(
                Cedula.id, Cedula.lote_id, Cedula.pais, Cedula.valor_facial, Cedula.ano, 
                Cedula.catalogo, Cedula.estado, Cedula.quantidade, 
                Cedula.martelo, Cedula.taxa_leilao, Cedula.data_compra, 
                Lote.frete, Lote.custos_extras, Vendedor.nome
            ).join(Lote, Cedula.lote_id == Lote.id)\
             .join(Vendedor, Lote.vendedor_id == Vendedor.id)\
             .order_by(Cedula.id.desc()).all()

            # 2. Calcula o total de subtotais de cada lote (para o rateio do frete)
            totais_subtotais_lotes = {}
            for r in resultados:
                if r.lote_id not in totais_subtotais_lotes:
                    totais_subtotais_lotes[r.lote_id] = 0
                valor_base = r.martelo * r.quantidade
                subtotal = valor_base + (valor_base * (r.taxa_leilao / 100))
                totais_subtotais_lotes[r.lote_id] += subtotal

            # 3. Formata os dados já calculando o Custo Final
            lista_dados = []
            for r in resultados:
                frete_total = r.frete + r.custos_extras
                total_subtotal_lote = totais_subtotais_lotes[r.lote_id]
                
                custos = CustoService.calcular(
                    martelo=r.martelo,
                    quantidade=r.quantidade,
                    taxa_leilao=r.taxa_leilao,
                    frete_total=frete_total,
                    total_subtotal_lote=total_subtotal_lote
                )

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
                    'vendedor': r.nome,
                    'custo_final': custos['custo_final']
                })

            # 4. Verifica o formato e retorna o arquivo correto
            if formato == 'csv':
                exportador = ExportadorDados(lista_dados)
                return Response(exportador.para_csv(), mimetype='text/csv', 
                                headers={"Content-Disposition": "attachment;filename=relatorio_cedulas.csv"})
            elif formato == 'json':
                exportador = ExportadorDados(lista_dados)
                return Response(exportador.para_json(), mimetype='application/json')
            elif formato == 'txt':
                exportador = ExportadorDados(lista_dados)
                return Response(exportador.para_txt(), mimetype='text/plain')
            elif formato == 'pdf':
                # 👇 AQUI ESTÁ O AJUSTE: Passamos as opções escolhidas pelo usuário
                pdf_buffer = PDFExportService.gerar_relatorio(
                    lista_dados, 
                    incluir_grafico, 
                    incluir_lista, 
                    incluir_total
                )
                return Response(
                    pdf_buffer,
                    mimetype='application/pdf',
                    headers={"Content-Disposition": "attachment;filename=relatorio_cedulas.pdf"}
                )
            else:
                return {'erro': 'Formato não suportado. Use csv, json, txt ou pdf.'}, 400
                
        except Exception as e:
            return {'erro': str(e)}, 500