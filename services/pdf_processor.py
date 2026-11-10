import pdfplumber
import re
import os
from dicionario import traduzir_estado, ESTADOS_CONSERVACAO

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
        
        # Só salva o debug se a variável de ambiente estiver ligada (Opcional)
        if os.getenv('DEBUG_PDF'):
            with open("debug_pdf.txt", "w", encoding="utf-8") as f:
                f.write(self.texto_completo)
        
        return self.texto_completo

    def extrair_cedulas(self):
        linhas = self.texto_completo.split('\n')
        cedulas_extraidas = []
        
        data_compra_global = ""
        match_data = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', self.texto_completo)
        if match_data:
            data_compra_global = match_data.group(1)

        linhas = [l.strip() for l in linhas if l.strip()]

        i = 0
        while i < len(linhas):
            linha = linhas[i]
            
            if any(palavra in linha.lower() for palavra in ['totais', 'desconto', 'pago', 'pendente', 'total final']):
                i += 1
                continue

            match = re.match(r'^(\d{4,5})\s*-\s*(.*)', linha)
            
            if match:
                lote = match.group(1)
                texto_bloco = match.group(2).strip()
                
                if (i + 1) < len(linhas):
                    proxima_linha = linhas[i+1]
                    if not re.match(r'^\d{4,5}\s*-', proxima_linha):
                        texto_bloco += " " + proxima_linha
                        i += 1 
                
                ano = ""
                match_ano = re.search(r'\b(19|20)\d{2}(?:\s*-\s*(19|20)\d{2})?\b', texto_bloco)
                if match_ano:
                    ano = match_ano.group(0).replace(' ', '')
                    texto_bloco = texto_bloco.replace(match_ano.group(0), '')

                # CORREÇÃO DO VALOR: Agora aceita ponto de milhar e vírgula decimal
                match_valor = re.search(r'R\$\s*([\d\.]+(?:,\d{2})?)', texto_bloco)
                if not match_valor:
                    i += 1
                    continue
                
                valor = self._converter_valor(match_valor.group(1))
                texto_bloco = texto_bloco.replace(match_valor.group(0), '')

                match_pais = re.match(r'^([A-Za-zÀ-ÿ\s]+?)(?:\s*-|\s*\d)', texto_bloco)
                if match_pais:
                    pais = match_pais.group(1).strip()
                    texto_bloco = texto_bloco.replace(pais, '', 1).strip()
                else:
                    pais = "Desconhecido"

                texto_bloco = re.sub(r'R\$\s*[\d\.\,]+', '', texto_bloco)

                estado = traduzir_estado(texto_bloco) or "R"
                for sigla, variacoes in ESTADOS_CONSERVACAO.items():
                    for v in variacoes:
                        texto_bloco = re.sub(rf'\b{re.escape(v)}\b', '', texto_bloco, flags=re.IGNORECASE)

                texto_bloco = texto_bloco.replace('polímero', '').replace('polimero', '').replace('soberba', '')
                texto_bloco = re.sub(r'\d+,\d+', '', texto_bloco)
                texto_bloco = texto_bloco.replace('R$', '').replace('(', '').replace(')', '').replace('-', ' ').strip()
                
                palavras = texto_bloco.split()
                descricao_palavras = []
                quantidade = 1
                
                for p in palavras:
                    if p.isdigit() and 1 <= int(p) <= 9 and len(descricao_palavras) > 0:
                        quantidade = int(p)
                    elif p == '0':
                        continue
                    else:
                        descricao_palavras.append(p)
                
                descricao_final = ' '.join(descricao_palavras).strip().title()

                cedulas_extraidas.append({
                    'codigo': lote, 'pais': pais, 'descricao': descricao_final, 'ano': ano,
                    'estado': estado, 'pick': "", 'quantidade': quantidade, 'valor': valor, 'data': data_compra_global
                })
                
            i += 1 
            
        return cedulas_extraidas

    def _converter_valor(self, valor_str):
        """Blindagem para converter R$ 1.200,50 ou 120.00 corretamente"""
        if ',' in valor_str:
            valor_str = valor_str.replace('.', '').replace(',', '.')
        elif '.' in valor_str:
            partes = valor_str.split('.')
            if len(partes[-1]) != 2:
                valor_str = valor_str.replace('.', '')
        try:
            return float(valor_str)
        except ValueError:
            return 0.0