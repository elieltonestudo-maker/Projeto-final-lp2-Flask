from rapidocr import RapidOCR
import io
import numpy as np
from PIL import Image

# Carrega o motor do RapidOCR
engine = RapidOCR()

class ProcessadorImagem:
    def __init__(self, arquivo_imagem):
        self.arquivo = arquivo_imagem

    def extrair_texto(self):
        try:
            # Lê os bytes da imagem e converte para o formato que o RapidOCR entende
            image_bytes = self.arquivo.read()
            img = Image.open(io.BytesIO(image_bytes))
            img_array = np.array(img)

            # Executa a leitura
            result = engine(img_array)
            
            # O RapidOCR retorna um objeto. A lista de textos fica em result.txts
            if result and result.txts:
                # Junta todas as linhas de texto encontradas
                return "\n".join(result.txts)
            return ""
            
        except Exception as e:
            raise Exception(f"Erro no RapidOCR: {str(e)}")