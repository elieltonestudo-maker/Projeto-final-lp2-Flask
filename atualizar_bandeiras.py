import os
import unicodedata
from PIL import Image
import json

# --- CONFIGURAÇÕES DE PASTAS ---
DESTINO = os.path.join("static", "img", "flags") 
ARQUIVO_MAPA = os.path.join("static", "js", "mapa_bandeiras.js")

# --- DICIONÁRIO DE TRADUÇÃO ---
TRADUCOES = {
    "AFGHANISTAN": "AFEGANISTAO", "GERMANY": "ALEMANHA", "ARGENTINA": "ARGENTINA",
    "AUSTRALIA": "AUSTRALIA", "AUSTRIA": "AUSTRIA", "BELGIUM": "BELGICA",
    "BRAZIL": "BRASIL", "CANADA": "CANADA", "CHILE": "CHILE", "CHINA": "CHINA",
    "COLOMBIA": "COLOMBIA", "CUBA": "CUBA", "DENMARK": "DINAMARCA",
    "EGYPT": "EGITO", "SPAIN": "ESPANHA", "USA": "ESTADOS_UNIDOS", 
    "ESTADOS_UNIDOS_DA_AMERICA": "ESTADOS_UNIDOS", "UNITED_STATES": "ESTADOS_UNIDOS",
    "FRANCE": "FRANCA", "GREECE": "GRECIA", "NETHERLANDS": "HOLANDA",
    "HUNGARY": "HUNGRIA", "INDIA": "INDIA", "INDONESIA": "INDONESIA",
    "IRAN": "IRA", "IRAQ": "IRAQUE", "IRELAND": "IRLANDA", "ISRAEL": "ISRAEL",
    "ITALY": "ITALIA", "JAPAN": "JAPAO", "MEXICO": "MEXICO", "NIGERIA": "NIGERIA",
    "NORWAY": "NORUEGA", "NEW_ZEALAND": "NOVA_ZELANDIA", "PAKISTAN": "PAQUISTAO",
    "PARAGUAY": "PARAGUAI", "PERU": "PERU", "POLAND": "POLONIA", "PORTUGAL": "PORTUGAL",
    "UNITED_KINGDOM": "REINO_UNIDO", "CZECH_REPUBLIC": "REPUBLICA_TCHECA",
    "ROMANIA": "ROMENIA", "RUSSIA": "RUSSIA", "SWEDEN": "SUECIA", "SWITZERLAND": "SUICA",
    "THAILAND": "TAILANDIA", "TURKEY": "TURQUIA", "UKRAINE": "UCRANIA",
    "URUGUAY": "URUGUAI", "VENEZUELA": "VENEZUELA", "VIETNAM": "VIETNA",
    "CZECHOSLOVAKIA": "TCHECOSLOVAQUIA", "YUGOSLAVIA": "IUGOSLAVIA",
    "SOUTH_AFRICA": "AFRICA_DO_SUL", "CAPE_VERDE": "CABO_VERDE",
    "BOSNIA_AND_HERZEGOVINA": "BOSNIA_E_HERZEGOVINA", "KOREA,_SOUTH": "COREIA_DO_SUL",
    "NORTH_MACEDONIA": "MACEDONIA_DO_NORTE", "SAINT_KITTS_AND_NEVIS": "SAO_CRISTOVAO_E_NEVIS",
    "TRINIDAD_AND_TOBAGO": "TRINIDAD_E_TOBAGO"
}

def limpar_nome(texto):
    # Remove acentos e formata para maiúsculo com underline
    texto_sem_acento = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    return texto_sem_acento.upper().replace(" ", "_").replace("-", "_")

def processar_bandeiras():
    if not os.path.exists(DESTINO):
        print(f"❌ A pasta {DESTINO} não existe.")
        return

    arquivos = os.listdir(DESTINO)
    renomeados = 0

    print("⏳ Traduzindo e renomeando bandeiras na pasta final...\n")

    # 1. Renomeia os arquivos dentro da própria pasta static/img/flags
    for arquivo in arquivos:
        if arquivo.lower().endswith('.png'):
            nome_base = os.path.splitext(arquivo)[0]
            nome_limpo = limpar_nome(nome_base)
            
            # Se o nome estiver no dicionário de tradução, renomeia
            if nome_limpo in TRADUCOES:
                nome_final_pt = TRADUCOES[nome_limpo]
                novo_nome = f"{nome_final_pt}.png"
                
                caminho_antigo = os.path.join(DESTINO, arquivo)
                caminho_novo = os.path.join(DESTINO, novo_nome)
                
                # Se o arquivo com o nome novo ainda não existe, renomeia
                if not os.path.exists(caminho_novo):
                    try:
                        os.rename(caminho_antigo, caminho_novo)
                        print(f"✅ Renomeado: {arquivo} -> {novo_nome}")
                        renomeados += 1
                    except Exception as e:
                        print(f"❌ Erro ao renomear {arquivo}: {e}")

    # 2. Atualiza o arquivo mapa_bandeiras.js com os nomes atualizados
    print("\n🔄 Atualizando o mapa de bandeiras para o JavaScript...")
    
    mapa_final = {}
    # Lê novamente a pasta agora que os arquivos foram renomeados
    for arq in os.listdir(DESTINO):
        if arq.lower().endswith('.png'):
            nome_sem_ext = os.path.splitext(arq)[0]
            mapa_final[nome_sem_ext] = arq
            mapa_final[nome_sem_ext.replace("_", " ").title()] = arq

    os.makedirs(os.path.dirname(ARQUIVO_MAPA), exist_ok=True)
    with open(ARQUIVO_MAPA, "w", encoding="utf-8") as f:
        f.write("// Arquivo gerado automaticamente pelo Python\n")
        f.write("const MAPA_BANDEIRAS_LOCAIS = ")
        f.write(json.dumps(mapa_final, indent=4, ensure_ascii=False))
        f.write(";\n")
        
    print(f"🎉 Finalizado! {renomeados} bandeiras traduzidas e renomeadas.")
    print(f"✅ Arquivo '{ARQUIVO_MAPA}' atualizado com {len(mapa_final)} nomes mapeados.")

if __name__ == "__main__":
    processar_bandeiras()