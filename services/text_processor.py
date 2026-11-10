import re
from dicionario import traduzir_estado, ESTADOS_CONSERVACAO

class ProcessadorTexto:
    def __init__(self, texto):
        self.texto = texto

    def extrair_cedulas(self):
        cedulas_extraidas = []
        linhas = self.texto.split('\n')
        linhas = [l.strip() for l in linhas if l.strip()]

        # Busca a data global (ex: data do recibo)
        data_compra = ""
        match_data = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', self.texto)
        if match_data:
            data_compra = match_data.group(1)

        paises_compostos = [
            "Papua Nova Guiné", "Ilhas Salomão", "Reino Unido", "Nova Zelândia", 
            "África do Sul", "Coreia do Sul", "Coreia do Norte", "Costa Rica", 
            "El Salvador", "Estados Unidos", "Transnistria", "Guatemala", "Nigéria", 
            "Tchecoslováquia", "Serra Leoa", "Afeganistão", "Coréia do Sul", 
            "Seychelles", "Hungria", "Vietnã do Sul"
        ]
        lixos_qualquer_lugar = [
            "Rara", "Polimero", "Polímero", "Estrangeira", "Edição", "Comemorativa", 
            "Aniversário", "Universidade", "Dr.", "Escassa", "Muito", "Difícil", 
            "Bastante", "Atrativa", "Estimativa", "Tipo", "Pick", "Flor de Estampa"
        ]

        i = 0
        while i < len(linhas):
            linha = linhas[i]
            
            # Ignora linhas de rodapé, frete ou totais
            if any(palavra in linha.lower() for palavra in ['sedex', 'frete', 'total', 'desconto', 'pago', 'pendente', 'dados bancários', 'pix:', 'banco', 'pac', 'jadlog', 'mini envio']):
                i += 1
                continue
            
            # NOVO: Tenta achar o padrão "Lote: 123" OU o padrão "2096 - Filipinas - 50 pisos 1 R$ 20,00..."
            match_lote = re.match(r'Lote:\s*(\d+)', linha, re.IGNORECASE)
            match_pdf = re.match(r'^(\d{4,5})\s*-\s*(.*)', linha)
            
            lote = None
            descricao_completa = ""
            valor = 0.0

            if match_lote:
                lote = match_lote.group(1)
                if (i + 1) < len(linhas):
                    descricao_completa = linhas[i+1]
                if (i + 2) < len(linhas):
                    linha_valor = linhas[i+2]
                    match_valor = re.search(r'R\$\s*([\d\.,]+)', linha_valor)
                    if match_valor:
                        valor = self._converter_valor(match_valor.group(1))
                    i += 3
            elif match_pdf:
                lote = match_pdf.group(1)
                descricao_completa = match_pdf.group(2).strip()
                
                # Junta a linha de baixo (onde geralmente cai o ano e o estado)
                if (i + 1) < len(linhas) and not re.match(r'^\d{4,5}\s*-', linhas[i+1]):
                    descricao_completa += " " + linhas[i+1]
                    i += 1
                
                # Pega o primeiro valor R$ da linha (o valor unitário)
                match_valor = re.search(r'R\$\s*([\d\.,]+)', descricao_completa)
                if match_valor:
                    valor = self._converter_valor(match_valor.group(1))
                    descricao_completa = descricao_completa.replace(match_valor.group(0), '')

                # Corta tudo o que vier depois do próximo R$ (Desconto, Total, etc)
                descricao_completa = descricao_completa.split('R$')[0].strip()    
                
                i += 1
            else:
                i += 1
                continue

            if descricao_completa and valor > 0:
                # Limpeza da descrição
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

                # Remove quantidades soltas do final (ex: " 1")
                palavras_desc = descricao_final.split()
                if palavras_desc and (len(palavras_desc[-1]) <= 3 or '/' in palavras_desc[-1]):
                     palavras_desc.pop()

                descricao_final = ' '.join(palavras_desc).strip()
                descricao_final = re.sub(r'\s+', ' ', descricao_final).strip()

                cedulas_extraidas.append({
                    'codigo': lote, 'pais': pais, 'descricao': descricao_final, 'ano': ano,
                    'estado': estado, 'pick': pick, 'quantidade': 1, 'valor': valor, 'data': data_compra
                })

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