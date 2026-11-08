from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Vendedor(db.Model):
    __tablename__ = 'vendedores'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)

    def __init__(self, nome):
        self.nome = nome

class Lote(db.Model):
    __tablename__ = 'lotes'
    
    id = db.Column(db.Integer, primary_key=True)
    vendedor_id = db.Column(db.Integer, db.ForeignKey('vendedores.id'), nullable=False)
    tipo = db.Column(db.String(50))
    origem = db.Column(db.String(50)) # <-- NOVA COLUNA
    frete = db.Column(db.Float, default=0.0)
    custos_extras = db.Column(db.Float, default=0.0)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)

    # ... relacionamentos ...

    def __init__(self, vendedor_id, tipo, origem, frete, custos_extras): # <-- Adicione origem aqui
        self.vendedor_id = vendedor_id
        self.tipo = tipo
        self.origem = origem
        self.frete = frete
        self.custos_extras = custos_extras

class Cedula(db.Model):
    __tablename__ = 'cedulas'
    
    id = db.Column(db.Integer, primary_key=True)
    lote_id = db.Column(db.Integer, db.ForeignKey('lotes.id'), nullable=False)
    
    pais = db.Column(db.String(100))
    valor_facial = db.Column(db.String(100))
    ano = db.Column(db.String(20))
    catalogo = db.Column(db.String(50))
    estado = db.Column(db.String(20))
    
    # ESSAS TRÊS COLUNAS SÃO AS QUE ESTÃO FALTANDO
    quantidade = db.Column(db.Integer, default=1)
    data_compra = db.Column(db.String(20))
    ref_lote = db.Column(db.String(50))
    
    martelo = db.Column(db.Float, default=0.0)
    taxa_leilao = db.Column(db.Float, default=0.0)

    def __init__(self, lote_id, pais, valor_facial, ano, catalogo, estado, quantidade, data_compra, ref_lote, martelo, taxa_leilao=0.0):
        self.lote_id = lote_id
        self.pais = pais
        self.valor_facial = valor_facial
        self.ano = ano
        self.catalogo = catalogo
        self.estado = estado
        self.quantidade = quantidade
        self.data_compra = data_compra
        self.ref_lote = ref_lote
        self.martelo = martelo
        self.taxa_leilao = taxa_leilao

    @property
    def subtotal(self):
        return self.martelo + (self.martelo * (self.taxa_leilao / 100))

    def calcular_rateio_frete(self, valor_total_lote):
        if valor_total_lote == 0:
            return 0.0
        valor_frete_total = self.lote.frete + self.lote.custos_extras
        return (self.martelo / valor_total_lote) * valor_frete_total

    def calcular_custo_final(self, valor_total_lote):
        return self.subtotal + self.calcular_rateio_frete(valor_total_lote)