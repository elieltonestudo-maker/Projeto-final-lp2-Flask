# --- DICIONÁRIO DE TRADUÇÃO DE ESTADOS DE CONSERVAÇÃO ---
# Mapeia variações em português e inglês para a sigla oficial do sistema.

ESTADOS_CONSERVACAO = {
    "FE": [
        "FE", "FLOR DE ESTAMPA", "FLOR", "UNC", "UNCIRCULATED", "CU", "CRISP UNCIRCULATED"
    ],
    "S/FE": [
        "S/FE", "SOBERBA/FLOR", "SOBERBA/FLOR DE ESTAMPA", "AU", "ABOUT UNCIRCULATED", "S/FLOR", "SOB/FE"
    ],
    "S": [
        "S", "SOBERBA", "XF", "EF", "EXTREMELY FINE"
    ],
    "MBC/S": [
        "MBC/S", "MUITO BEM/SOBERBA", "VF/XF", "MUITO BEM / SOBERBA"
    ],
    "MBC": [
        "MBC", "MUITO BEM CONSERVADA", "MUITO BEM", "VF", "VERY FINE"
    ],
    "BC/MBC": [
        "BC/MBC", "BEM/MUITO BEM", "F/VF", "BEM / MUITO BEM"
    ],
    "BC": [
        "BC", "BEM CONSERVADA", "BEM", "F", "FINE"
    ],
    "R": [
        "R", "REGULAR", "G", "GOOD"
    ],
    "UTG": [
        "UTG", "UM TANTO GASTA", "P", "POOR", "FR", "FAIR"
    ]
}

def traduzir_estado(texto_pdf):
    """
    Recebe um texto (ex: 'Sob/FE' ou 'XF') e retorna a sigla oficial (ex: 'S/FE' ou 'S').
    Se não encontrar nada, retorna 'R'.
    """
    if not texto_pdf:
        return "R"
        
    import re
    texto_upper = texto_pdf.upper()
    
    # Ordena a lista para buscar os termos mais longos primeiro (ex: "SOB/FE" antes de "FE")
    todas_variacoes = []
    for sigla, variacoes in ESTADOS_CONSERVACAO.items():
        for v in variacoes:
            todas_variacoes.append((v, sigla))
            
    # Ordena do maior para o menor
    todas_variacoes.sort(key=lambda x: len(x[0]), reverse=True)

    for variacao, sigla in todas_variacoes:
        # O \b garante que estamos buscando a palavra exata (ex: "S" não acha em "PESOS")
        if re.search(rf'\b{re.escape(variacao)}\b', texto_upper):
            return sigla
            
    return "R"