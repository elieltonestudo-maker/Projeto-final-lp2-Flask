import os
import zipfile
import subprocess
from flask import send_file

class SistemaService:
    @staticmethod
    def gerar_backup(app):
        try:
            nome_arquivo = 'backup_cedulas.zip'
            caminho_db = os.path.join(app.instance_path, 'cedulas.db')
            
            # Verifica se o banco está na pasta instance ou na raiz
            if not os.path.exists(caminho_db):
                caminho_db = 'cedulas.db'

            if not os.path.exists(caminho_db):
                return {'erro': 'Banco de dados não encontrado.'}, 404

            with zipfile.ZipFile(nome_arquivo, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(caminho_db, arcname='cedulas.db')
            
            return send_file(nome_arquivo, as_attachment=True)
        except Exception as e:
            return {'erro': f'Erro ao gerar backup: {str(e)}'}, 500

    @staticmethod
    def atualizar_bandeiras():
        try:
            resultado = subprocess.run(['python', 'atualizar_bandeiras.py'], capture_output=True, text=True)
            if resultado.returncode == 0:
                return {'mensagem': 'Bandeiras atualizadas com sucesso!'}, 200
            else:
                return {'erro': f'Erro no script: {resultado.stderr}'}, 500
        except Exception as e:
            return {'erro': str(e)}, 500