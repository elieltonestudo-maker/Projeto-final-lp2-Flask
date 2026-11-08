# Dicionário focado em traduzir apenas os estados "seguros" (FE e S).
# Os outros (MBC, BC, R) serão preenchidos como padrão "R" e o usuário ajusta na tela se quiser.
ESTADOS_CONSERVACAO = {
    "FE": [
        "FE", "FLOR DE ESTAMPA", "FLOR", "UNC", "UNCIRCULATED", "CU"
    ],
    "S/FE": [
        "S/FE", "SOBERBA/FLOR", "SOBERBA/FLOR DE ESTAMPA", "AU"
    ],
    "S": [
        "S", "SOBERBA", "XF", "EF", "EXTREMELY FINE"
    ]
}

def traduzir_estado(texto_pdf):
    if not texto_pdf:
        return "R" # Padrão se não encontrar nada
        
    texto_upper = texto_pdf.upper()
    
    # Ordena do maior para o menor para não confundir "FLOR" com "F"
    todas_variacoes = []
    for sigla, variacoes in ESTADOS_CONSERVACAO.items():
        for v in variacoes:
            todas_variacoes.append((v, sigla))
    todas_variacoes.sort(key=lambda x: len(x[0]), reverse=True)

    import re
    for variacao, sigla in todas_variacoes:
        if re.search(rf'\b{re.escape(variacao)}\b', texto_upper):
            return sigla
            
    return "R" # Se não achou FE, S/FE ou S, retorna R como padrão