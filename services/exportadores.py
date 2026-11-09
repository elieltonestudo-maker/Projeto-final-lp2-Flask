import csv
import io
import json

class ExportadorDados:
    def __init__(self, dados):
        self.dados = dados

    def para_csv(self):
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        
        writer.writerow(['ID', 'País', 'Valor Facial', 'Ano', 'Catálogo', 'Estado', 'Qtd', 'Martelo', 'Data', 'Vendedor'])
        
        for r in self.dados:
            writer.writerow([
                r.get('id'), r.get('pais'), r.get('descricao'), r.get('ano'), 
                r.get('catalogo'), r.get('estado'), r.get('quantidade'), 
                r.get('martelo'), r.get('data'), r.get('vendedor')
            ])
            
        output.seek(0)
        return output.getvalue()

    def para_json(self):
        return json.dumps(self.dados, ensure_ascii=False, indent=4)

    def para_txt(self):
        linhas = ["RELATÓRIO DE CÉDULAS", "=" * 40]
        for r in self.dados:
            linhas.append(f"{r.get('pais')} - {r.get('descricao')} - Qtd: {r.get('quantidade')} - {r.get('estado')}")
        return "\n".join(linhas)