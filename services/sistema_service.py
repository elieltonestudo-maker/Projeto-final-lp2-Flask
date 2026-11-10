import os
import io
import zipfile
import subprocess
import sys
import shutil
from flask import send_file, current_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Vendedor # Importante para o teste de validação

class SistemaService:
    @staticmethod
    def gerar_backup(app):
        try:
            caminho_db = os.path.join(app.instance_path, 'cedulas.db')
            if not os.path.exists(caminho_db):
                caminho_db = 'cedulas.db'

            if not os.path.exists(caminho_db):
                return {'erro': 'Banco de dados não encontrado.'}, 404

            memory_file = io.BytesIO()
            with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(caminho_db, arcname='cedulas.db')
            
            memory_file.seek(0)
            
            return send_file(
                memory_file,
                mimetype='application/zip',
                as_attachment=True,
                download_name='backup_cedulas.zip'
            )
        except Exception as e:
            return {'erro': f'Erro ao gerar backup: {str(e)}'}, 500

    @staticmethod
    def atualizar_bandeiras():
        try:
            resultado = subprocess.run(
                [sys.executable, 'atualizar_bandeiras.py'], 
                capture_output=True, text=True, timeout=60
            )
            if resultado.returncode == 0:
                return {'mensagem': 'Bandeiras atualizadas com sucesso!'}, 200
            else:
                return {'erro': f'Erro no script: {resultado.stderr}'}, 500
        except subprocess.TimeoutExpired:
            return {'erro': 'O script demorou muito para responder.'}, 500
        except Exception as e:
            return {'erro': str(e)}, 500

    @staticmethod
    def restaurar_backup(arquivo):
        if not arquivo or arquivo.filename == '':
            return {'erro': 'Nenhum arquivo selecionado.'}, 400
        
        if not arquivo.filename.endswith('.db'):
            return {'erro': 'O arquivo deve ter a extensão .db'}, 400

        # Define a pasta raiz do projeto onde o app.py está rodando
        pasta_raiz = current_app.root_path
        
        # O arquivo será salvo na mesma pasta do app.py, com o nome "banco_restaurado.db"
        arquivo_preparado = os.path.join(pasta_raiz, 'banco_restaurado.db')
        
        try:
            # 1. Salva o arquivo
            arquivo.save(arquivo_preparado)
            
            # 2. TESTE DE VALIDAÇÃO
            engine_teste = create_engine(f'sqlite:///{arquivo_preparado}')
            Session = sessionmaker(bind=engine_teste)
            session = Session()
            
            session.query(Vendedor).first()
            session.close()
            engine_teste.dispose()
            
            # 3. Retorna sucesso
            return {
                'mensagem': 'Backup validado com sucesso! O arquivo "banco_restaurado.db" foi salvo na raiz do seu projeto. '
                            'Para aplicar: 1) Feche o sistema. 2) Vá na pasta instance e apague o cedulas.db. '
                            '3) Mova o banco_restaurado.db para a pasta instance e renomeie para cedulas.db.'
            }, 200
            
        except Exception as e:
            if os.path.exists(arquivo_preparado):
                try:
                    os.remove(arquivo_preparado)
                except PermissionError:
                    pass
            
            if "not a database" in str(e):
                return {'erro': 'O arquivo enviado não é um banco de dados válido.'}, 400
            
            return {'erro': f'Erro ao validar o arquivo. Detalhe: {str(e)}'}, 400