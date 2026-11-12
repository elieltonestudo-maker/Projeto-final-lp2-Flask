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
            if any(palavra in linha.lower() for palavra in ['sedex', 'frete', 'total', 'desconto', 'pago', 'pendente', 'dados bancários', 'pix:', 'banco', 'pac', 'jadlog', 'mini envio', 'recibo', 'cliente', 'produto', 'qtd', 'unitário', 'totais:']):
                i += 1
                continue
            
            # ==========================================
            # LÓGICA 2: FORMATO PDF/RECIBO OU OCR (3067 - Sudão - ...)
            # ==========================================
            if re.match(r'^(\d{3,5})\s*-\s*(.*)', linha):
                cedula_ocr = self._processar_linha_ocr(linhas, i, data_compra)
                if cedula_ocr:
                    cedulas_extraidas.append(cedula_ocr)
                    i += 2 # Pula a linha de baixo (ano/estado)
                    continue
                else:
                    i += 1
                    continue

            # ==========================================
            # LÓGICA 1: FORMATO LEILÃO (Lote: 88)
            # ==========================================
            match_lote = re.match(r'Lote:\s*(\d+)', linha, re.IGNORECASE)
            if match_lote:
                lote = match_lote.group(1)
                descricao_completa = linhas[i+1] if (i+1) < len(linhas) else ""
                valor = 0.0
                if (i+2) < len(linhas):
                    match_valor = re.search(r'R\$\s*([\d\.,]+)', linhas[i+2])
                    if match_valor:
                        valor = self._converter_valor(match_valor.group(1))
                i += 3
            
            else:
                i += 1
                continue

            # ==========================================
            # LIMPEZA COMUM (Para Lógica 1 apenas)
            # ==========================================
            if descricao_completa and valor > 0:
                pick = ""
                match_pick = re.search(r'\b(P\s*-?\s*\d+[a-zA-Z]*)\b', descricao_completa, re.IGNORECASE)
                if match_pick:
                    pick = match_pick.group(1).upper().replace(' ', '')
                    descricao_completa = descricao_completa.replace(match_pick.group(0), '')

                match_ano = re.search(r'\b(1[6-9]\d{2}|20\d{2})\b', descricao_completa)
                ano = ""
                if match_ano:
                    ano = match_ano.group(0)
                    descricao_completa = descricao_completa.replace(ano, '')

                descricao = re.sub(r'^\s*C[ÉE]DULA\s+(Estrangeira|da|do|de|dos|das)?\s*[-]?\s*', '', descricao_completa, flags=re.IGNORECASE).strip()
                descricao = re.sub(r'^\s*C[ÉE]DULA\s+', '', descricao, flags=re.IGNORECASE).strip()
                descricao = re.sub(r'^\s*(dos|das|do|da|de)\s+', '', descricao, flags=re.IGNORECASE).strip()
                descricao = re.sub(r'\(.*?\)', '', descricao).strip()
                
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

    # ==========================================
    # FUNÇÃO EXCLUSIVA PARA O OCR
    # ==========================================
    def _processar_linha_ocr(self, linhas, i, data_compra):
        try:
            linha = linhas[i]
            match_ocr = re.match(r'^(\d{3,5})\s*-\s*(.*)', linha)
            lote = match_ocr.group(1)
            texto_descricao = match_ocr.group(2).strip()

            valor = 0.0
            ano = ""
            estado = "R"

            # 1. Procura o ano e o estado na PRÓPRIA linha do lote primeiro (Caso do Laos)
            match_ano_local = re.search(r'\b(19\d{2}|20[0-2]\d)\b', texto_descricao)
            if match_ano_local:
                ano = match_ano_local.group(0)
                # Remove o ano do texto para achar o estado
                resto = texto_descricao.replace(ano, '').strip()
                estado = traduzir_estado(resto) or "R"
                
                # Remove o estado do texto para limpar a descrição
                for sigla, variacoes in ESTADOS_CONSERVACAO.items():
                    for v in variacoes:
                        texto_descricao = re.sub(rf'\b{re.escape(v)}\b', '', texto_descricao, flags=re.IGNORECASE)
                
                texto_descricao = texto_descricao.replace(ano, '').strip()

            # 2. Limpa o valor R$ se estiver na mesma linha
            if 'R$' in texto_descricao:
                texto_descricao = texto_descricao.split('R$')[0].strip()
            
            # Remove o "1" (quantidade) solto no final
            texto_descricao = re.sub(r'\s+\b1\b\s*$', '', texto_descricao).strip()

            # 3. Vasculha as próximas 5 linhas em busca do Valor e (se não achou) do Ano
            for j in range(1, 6):
                if (i + j) < len(linhas):
                    prox_linha = linhas[i + j]
                    
                    # Procura o valor R$ (se não achou ainda)
                    if valor == 0.0:
                        match_v = re.search(r'R\$\s*([\d\.,]+)', prox_linha)
                        if match_v:
                            valor = self._converter_valor(match_v.group(1))
                    
                    # Se não achou o ano localmente, procura nas linhas de baixo
                    if not ano:
                        match_ano = re.search(r'\b(19\d{2}|20[0-2]\d)\b', prox_linha)
                        if match_ano:
                            ano = match_ano.group(0)
                            estado = traduzir_estado(prox_linha) or "R"
                    
                    # Se já achou tudo, para de vasculhar
                    if ano and valor > 0:
                        break

            # 4. Se o valor ainda for 0, tenta achar na linha original (caso o OCR tenha lido R$ junto)
            if valor == 0.0:
                match_v_local = re.search(r'R[S\$]\s*([\d\.,]+)', match_ocr.group(2))
                if match_v_local:
                    valor = self._converter_valor(match_v_local.group(1))

            # 5. Separa o País da Descrição pelo hífen
            partes_desc = texto_descricao.split(' - ')
            if len(partes_desc) >= 2:
                pais = partes_desc[0].strip()
                descricao_final = ' - '.join(partes_desc[1:]).strip().title()
            else:
                partes = texto_descricao.split()
                pais = partes[0] if partes else "Desconhecido"
                descricao_final = ' '.join(partes[1:]).strip().title()

            descricao_final = re.sub(r'\b1\b', '', descricao_final).strip()
            
            return {
                'codigo': lote, 'pais': pais, 'descricao': descricao_final, 'ano': ano,
                'estado': estado, 'pick': "", 'quantidade': 1, 'valor': valor, 'data': data_compra
            }
        except Exception:
            return None
        
    def _converter_valor(self, valor_str):
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