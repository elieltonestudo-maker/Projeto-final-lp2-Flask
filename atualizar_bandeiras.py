import os
import shutil
import unicodedata
from PIL import Image
import json

# --- CONFIGURAÇÕES DE PASTAS ---
ORIGEM_PNG = os.path.join("New_flags") # Pasta onde você salva as imagens baixadas
DESTINO = os.path.join("static", "img", "flags") # Pasta onde o sistema lê
ARQUIVO_MAPA = os.path.join("static", "js", "mapa_bandeiras.js")
LARGURA_MAXIMA = 40

# --- DICIONÁRIO DE TRADUÇÃO ---
# Adicione aqui os países que têm nomes diferentes do português
TRADUCOES = {
    "AFGHANISTAN": "AFEGANISTAO", "GERMANY": "ALEMANHA", "ARGENTINA": "ARGENTINA",
    "AUSTRALIA": "AUSTRALIA", "AUSTRIA": "AUSTRIA", "BELGIUM": "BELGICA",
    "BRAZIL": "BRASIL", "CANADA": "CANADA", "CHILE": "CHILE", "CHINA": "CHINA",
    "COLOMBIA": "COLOMBIA", "CUBA": "CUBA", "DENMARK": "DINAMARCA",
    "EGYPT": "EGITO", "SPAIN": "ESPANHA", "USA": "ESTADOS_UNIDOS", "ESTADOS_UNIDOS_DA_AMERICA": "ESTADOS_UNIDOS",
    "FRANCE": "FRANCA", "GREECE": "GRECIA", "NETHERLANDS": "HOLANDA",
    "HUNGARY": "HUNGRIA", "INDIA": "INDIA", "INDONESIA": "INDONESIA",
    "IRAN": "IRA", "IRAQ": "IRAQUE", "IRELAND": "IRLANDA", "ISRAEL": "ISRAEL",
    "ITALY": "ITALIA", "JAPAN": "JAPAO", "MEXICO": "MEXICO", "NIGERIA": "NIGERIA",
    "NORWAY": "NORUEGA", "NEW ZEALAND": "NOVA_ZELANDIA", "PAKISTAN": "PAQUISTAO",
    "PARAGUAY": "PARAGUAI", "PERU": "PERU", "POLAND": "POLONIA", "PORTUGAL": "PORTUGAL",
    "UNITED KINGDOM": "REINO_UNIDO", "CZECH REPUBLIC": "REPUBLICA_TCHECA",
    "ROMANIA": "ROMENIA", "RUSSIA": "RUSSIA", "SWEDEN": "SUECIA", "SWITZERLAND": "SUICA",
    "THAILAND": "TAILANDIA", "TURKEY": "TURQUIA", "UKRAINE": "UCRANIA",
    "URUGUAY": "URUGUAI", "VENEZUELA": "VENEZUELA", "VIETNAM": "VIETNA",
    "CZECHOSLOVAKIA": "TCHECOSLOVAQUIA", "YUGOSLAVIA": "IUGOSLAVIA",
    "SOVIET UNION": "UNIAO_SOVIETICA", "SOUTH AFRICA": "AFRICA_DO_SUL",
    "ANGOLA": "ANGOLA", "MOZAMBIQUE": "MOCAMBIQUE", "CAPE VERDE": "CABO_VERDE",
    "GUINEA-BISSAU": "GUINE_BISSAU", "SAO TOME E PRINCIPE": "SAO_TOME_E_PRINCIPE",
    "BOSNIA AND HERZEGOVINA": "BOSNIA_E_HERZEGOVINA", "KOREA, SOUTH": "COREIA_DO_SUL",
    "NORTH MACEDONIA": "MACEDONIA_DO_NORTE", "SAINT KITTS AND NEVIS": "SAO_CRISTOVAO_E_NEVIS",
    "TRINIDAD AND TOBAGO": "TRINIDAD_E_TOBAGO", "UNITED STATES": "ESTADOS_UNIDOS"
}

def limpar_nome(texto):
    # Remove acentos e formata para maiúsculo com underline
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').upper().replace(" ", "_").replace("-", "_")

def processar_bandeiras():
    if not os.path.exists(ORIGEM_PNG) or not os.path.exists(DESTINO):
        print("❌ Verifique se as pastas 'Bandeira_png' e 'static/img/flags' existem.")
        return

    # 1. Lê os arquivos que já existem no destino para não sobrescrever
    arquivos_existentes = set(os.listdir(DESTINO))
    arquivos_origem = os.listdir(ORIGEM_PNG)
    
    convertidos = 0
    pulados = 0

    print("⏳ Processando bandeiras...\n")

    for arquivo in arquivos_origem:
        if arquivo.lower().endswith(('.png', '.jpg', '.jpeg', '.tif')):
            nome_base = os.path.splitext(arquivo)[0]
            nome_limpo = limpar_nome(nome_base)
            
            # Traduz o nome se estiver no dicionário, senão usa o nome limpo
            nome_final_pt = TRADUCOES.get(nome_limpo, nome_limpo)
            arquivo_destino = f"{nome_final_pt}.png"
            
            # Se o arquivo já existe no destino, pula (economiza tempo)
            if arquivo_destino in arquivos_existentes:
                pulados += 1
                continue
                
            caminho_orig = os.path.join(ORIGEM_PNG, arquivo)
            caminho_dest = os.path.join(DESTINO, arquivo_destino)
            
            try:
                with Image.open(caminho_orig) as img:
                    img = img.convert("RGBA")
                    proporcao = LARGURA_MAXIMA / float(img.width)
                    nova_altura = int((float(img.height) * float(proporcao)))
                    img_redimensionada = img.resize((LARGURA_MAXIMA, nova_altura), Image.Resampling.LANCZOS)
                    img_redimensionada.save(caminho_dest, format="PNG", optimize=True)
                    
                print(f"✅ Importado e traduzido: {arquivo} -> {arquivo_destino}")
                convertidos += 1
            except Exception as e:
                print(f"❌ Erro ao converter {arquivo}: {e}")

    # 2. Atualiza o arquivo mapa_bandeiras.js
    print("\n🔄 Atualizando o mapa de bandeiras para o JavaScript...")
    
    mapa_final = {}
    for arq in os.listdir(DESTINO):
        if arq.lower().endswith('.png'):
            nome_sem_ext = os.path.splitext(arq)[0]
            # Cria duas versões no mapa: a com underline e a com espaços
            mapa_final[nome_sem_ext] = arq
            mapa_final[nome_sem_ext.replace("_", " ").title()] = arq

    os.makedirs(os.path.dirname(ARQUIVO_MAPA), exist_ok=True)
    with open(ARQUIVO_MAPA, "w", encoding="utf-8") as f:
        f.write("// Arquivo gerado automaticamente pelo Python\n")
        f.write("const MAPA_BANDEIRAS_LOCAIS = ")
        f.write(json.dumps(mapa_final, indent=4, ensure_ascii=False))
        f.write(";\n")
        
    print(f"🎉 Finalizado! {convertidos} novas bandeiras adicionadas. {pulados} já existiam e foram puladas.")
    print(f"✅ Arquivo '{ARQUIVO_MAPA}' atualizado com {len(mapa_final)} nomes mapeados.")

if __name__ == "__main__":
    processar_bandeiras()