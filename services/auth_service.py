import os
from flask import session

class AuthService:
    # Define a senha padrão ou busca de uma variável de ambiente
    SENHA_PADRAO = os.getenv('SISTEMA_SENHA', 'xpto')

    @staticmethod
    def verificar_senha(senha_digitada):
        return senha_digitada == AuthService.SENHA_PADRAO

    @staticmethod
    def fazer_login():
        # Cria uma sessão no Flask marcando que o usuário está logado
        session['logado'] = True

    @staticmethod
    def fazer_logout():
        # Remove a marcação de login
        session.pop('logado', None)

    @staticmethod
    def esta_logado():
        return session.get('logado', False)