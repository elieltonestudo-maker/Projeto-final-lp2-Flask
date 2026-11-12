# 🪙 Gestão Numismática - Sistema de Acervo de Cédulas

Este projeto é o trabalho final das disciplinas de **Estruturas de Dados** e **Linguagem de Programação 2**, do curso de **Inteligência Artificial** da **Fatec Rio Claro/SP**, sob orientação do professor **Orlando Saraiva Jr.**

O sistema é uma aplicação web local (desenvolvida em **Flask/Python**) para automatizar o cadastro, gestão e análise de cédulas colecionáveis. Ele permite a importação de dados, cálculo de rateio de frete, gestão de vendedores, controle de usuários com níveis de acesso e exportação de relatórios visuais em PDF.

---

## 🚀 Funcionalidades Principais

* **Autenticação Segura e Persistente:** Login e cadastro de usuários com senhas criptografadas (Hash). Utiliza arquivo `.env` para manter a sessão do usuário ativa mesmo após reiniciar o servidor.
* **Importação Inteligente:** Extração automática de dados (País, Valor, Ano, Estado, Martelo) a partir de PDFs de leilões, e-mails ou textos do WhatsApp. Suporte a OCR (RapidOCR) para cópia de imagens/prints.
* **Cálculo de Rateio Automático:** Distribuição proporcional de frete e custos extras baseada no subtotal de cada cédula do lote.
* **Edição Completa de Lotes:** Modal interativo que permite alterar dados do vendedor, frete e todas as cédulas do lote de uma só vez, recalculando os custos automaticamente.
* **Gestão de Acervo:** Pesquisa avançada por país, vendedor, estado e faixa de valor. Filtros dinâmicos e ordenação inteligente.
* **Relatórios em PDF:** Geração de relatórios com gráfico de barras (Top 10 Países), bandeiras, tabela detalhada e marca d'água.
* **Bandeiras Locais:** Sistema próprio de cache e tradução de bandeiras em formato PNG para carregamento rápido e offline.
* **Segurança e Backup:** Backup do banco de dados via arquivo ZIP e ferramenta de restauração com validação de integridade.

---

## 🛠️ Pré-requisitos

* [Python 3.10+](https://www.python.org/downloads/)
* [Git](https://git-scm.com/) (opcional)

---

## ⚙️ Como Executar o Projeto

### 1. Clonar o repositório (ou baixar o ZIP)
```bash
git clone https://github.com/elieltonestudo-maker/Projeto-final-lp2-Flask.git
cd Projeto-final-lp2-Flask

### 2. Criar e ativar o ambiente virtual
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate

### 3. Instalar as dependências
pip install -r requirements.txt

### 4. Configurar as Variáveis de Ambiente (.env)
Crie um arquivo chamado .env na raiz do projeto (na mesma pasta do app.py) e adicione a seguinte linha para garantir a persistência da sessão:

SECRET_KEY=sua-chave-secreta-super-segura-aqui

### 5. Executar o sistema
python app.py

O navegador abrirá automaticamente em http://127.0.0.1:5000.

---

## 🖥️ Como Usar o Sistema

### Primeiro Acesso (Criar Administrador)
1. Na tela de login, clique em **"Cadastre-se"**.
2. Crie seu usuário e senha.
3. Para se tornar Administrador, pare o servidor (Ctrl+C) e rode no terminal:
   python -c "from app import create_app; from models import db, Usuario; app = create_app(); app.app_context().push(); u = Usuario.query.filter_by(username='SEU_USUARIO').first(); u.is_admin = True; db.session.commit(); print('Admin ativado!')"
4. Inicie o sistema novamente (python app.py). O menu **Gerenciar Usuários** estará disponível no ⚙️.

### 🧪 Roteiro de Teste (Com Arquivos de Exemplo)
Na pasta `ARQUIVOS_TESTE/` do projeto, existem arquivos `.docx` com exemplos de recibos de compra (COMPRA1, COMPRA2, etc.) para testar a inteligência do sistema.

**Passo a passo para testar:**
1. Abra um dos arquivos `.docx` no Microsoft Word (ou Google Docs).
2. Selecione todo o texto (Ctrl+A) e copie (Ctrl+C).
3. No sistema, vá na aba **REGISTRAR**.
4. Clique em **📥 Importar Texto**.
5. Cole o texto na caixa e clique em **Processar Texto**.
6. O sistema vai extrair os países, valores e anos automaticamente. Se precisar, ajuste a data e o frete.
7. Clique em **SALVAR LOTE COMPLETO**.
8. Vá para a aba **PESQUISAR** e veja os dados no gráfico e na tabela.
9. Exporte um **Relatório PDF** com gráfico e bandeiras para ver a geração do documento.

---

## 📂 Estrutura do Projeto


Projeto-final-lp2-Flask/
│
├── app.py                  # Rotas Flask e inicialização
├── models.py               # Modelos do Banco de Dados (SQLAlchemy)
├── requirements.txt        # Dependências do projeto
├── atualizar_bandeiras.py  # Script para traduzir e redimensionar bandeiras
├── .env                    # Variáveis de ambiente (SECRET_KEY)
│
├── services/               # Regras de Negócio (OOP)
│   ├── auth_service.py
│   ├── custo_service.py
│   ├── pdf_processor.py
│   ├── text_processor.py
│   ├── image_processor.py
│   ├── lote_service.py
│   ├── relatorio_service.py
│   └── ...
│
├── static/                 
│   ├── js/mapa_bandeiras.js
│   └── img/flags/          # Bandeiras em PNG
│
├── templates/              # Arquivos HTML (Login, Index, etc)
└── instance/               # Banco de dados SQLite (gerado auto)

---

## 🧠 Tecnologias e Bibliotecas

* **Linguagem:** Python 3.10+ e JavaScript.
* **Framework Web:** Flask.
* **Estrutura de Dados / ORM:** SQLAlchemy (mapeamento objeto-relacional).
* **Banco de Dados:** SQLite.
* **Processamento de Dados:** Pdfplumber, RapidOCR, Regex (para parsing de texto).
* **Geração de PDF:** ReportLab, Matplotlib (gráficos), PyPDF2 (carimbo/numeração), Pillow (bandeiras).

---

## 👨‍🏫 Créditos Acadêmicos

* **Instituição:** Fatec Rio Claro/SP
* **Curso:** Inteligência Artificial
* **Disciplinas:** Estruturas de Dados / Linguagem de Programação 2
* **Professor:** Orlando Saraiva Jr.
* **Autor:** Elielton Barbosa (RA: [Seu RA])