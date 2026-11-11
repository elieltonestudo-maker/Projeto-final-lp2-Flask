from flask import session
from models import db, Usuario

class AuthService:
    @staticmethod
    def cadastrar(username, senha, confirmar_senha):
        username = username.strip()
        if not username or not senha:
            return {'erro': 'Preencha todos os campos.'}, 400
        if senha != confirmar_senha:
            return {'erro': 'As senhas não coincidem.'}, 400
        if len(senha) < 4:
            return {'erro': 'A senha deve ter pelo menos 4 caracteres.'}, 400

        # Verifica se o usuário já existe
        existente = Usuario.query.filter_by(username=username).first()
        if existente:
            return {'erro': 'Este nome de usuário já está em uso.'}, 400

        try:
            novo_usuario = Usuario(username=username)
            novo_usuario.set_password(senha)
            db.session.add(novo_usuario)
            db.session.commit()
            return {'mensagem': 'Usuário cadastrado com sucesso!'}, 201
        except Exception as e:
            db.session.rollback()
            return {'erro': str(e)}, 500

    @staticmethod
    def verificar_login(username, senha):
        usuario = Usuario.query.filter_by(username=username.strip()).first()
        if usuario and usuario.check_password(senha):
            session['logado'] = True
            session['usuario_nome'] = usuario.username
            return True
        return False

    @staticmethod
    def fazer_logout():
        session.pop('logado', None)
        session.pop('usuario_nome', None)

    @staticmethod
    def esta_logado():
        return session.get('logado', False)