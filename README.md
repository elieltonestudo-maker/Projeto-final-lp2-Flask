# 🪙 Gestão Numismática - Sistema de Acervo de Cédulas

Este projeto é o trabalho final das disciplinas de **Estruturas de Dados** e **Linguagem de Programação 2**, do curso de **Inteligência Artificial** da **Fatec Rio Claro/SP**, sob orientação do professor **Orlando Saraiva Jr.**

O sistema é uma aplicação web local (desenvolvida em **Flask/Python**) para automatizar o cadastro, gestão e análise de cédulas colecionáveis. Ele permite a importação automática de dados de recibos (PDF/Texto), cálculo de rateio de frete, gestão de vendedores, controle de usuários com níveis de acesso e exportação de relatórios visuais em PDF.

---

## 🚀 Funcionalidades Principais

* **Autenticação Segura:** Login e cadastro de usuários com senhas criptografadas (Hash) e níveis de acesso (Administrador / Comum).
* **Importação Inteligente:** Extração automática de dados (País, Valor, Ano, Estado, Martelo) a partir de PDFs de leilões, e-mails ou textos do WhatsApp, usando Regex avançado.
* **Cálculo de Rateio:** Distribuição automática de frete e custos extras proporcional ao valor das cédulas.
* **Gestão de Acervo:** Pesquisa avançada por país, vendedor, estado e faixa de valor.
* **Relatórios em PDF:** Geração de relatórios com gráfico de barras (Top 10 Países), bandeiras, tabela detalhada e marca d'água, com opção de escolher o que incluir.
* **Segurança e Backup:** Backup do banco de dados e ferramenta de restauração com validação de integridade.

---

## 🛠️ Pré-requisitos

Antes de começar, você precisará ter instalado em sua máquina:
* [Python 3.10+](https://www.python.org/downloads/)
* [Git](https://git-scm.com/) (opcional, para clonar o repositório)
* [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (Opcional - necessário apenas para importar via imagem)

---

## ⚙️ Como Executar o Projeto (Passo a Passo)

Siga os passos abaixo no terminal do seu sistema operacional (recomendado usar o VS Code).

### 1. Clonar o repositório (ou baixar o ZIP)
git clone https://github.com/seu-usuario/Projeto-final-lp2-Flask.git
cd Projeto-final-lp2-Flask

### 2. Criar e ativar o ambiente virtual
python -m venv .venv

# Ativar no Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Ativar no Linux/Mac
source .venv/bin/activate

### 3. Instalar as dependências
Com o ambiente virtual ativado, instale as bibliotecas necessárias:
pip install -r requirements.txt

### 4. Configurar as variáveis de ambiente (Opcional)
O sistema gera uma SECRET_KEY aleatória a cada execução. Para produção, crie um arquivo .env na raiz do projeto e defina:
SECRET_KEY=sua-chave-secreta-aqui
FLASK_ENV=development

### 5. Executar o sistema
python app.py

O navegador abrirá automaticamente no endereço http://127.0.0.1:5000.

---

## 🖥️ Como Usar o Sistema

### Primeiro Acesso
1. Na tela de login, clique em **"Cadastre-se"**.
2. Crie seu usuário e senha. O primeiro usuário criado é um usuário comum.
3. **Para se tornar Administrador:** Após criar a conta, pare o servidor (Ctrl+C) e rode o comando no terminal:
python -c "from app import create_app; from models import db, Usuario; app = create_app(); app.app_context().push(); u = Usuario.query.filter_by(username='SEU_USUARIO').first(); u.is_admin = True; db.session.commit(); print('Admin ativado!')"
4. Inicie o sistema novamente (python app.py). Agora, ao logar, a opção **Gerenciar Usuários** estará disponível no menu ⚙️.

### Importando Dados (Aba REGISTRAR)
1. **Importar PDF:** Selecione o PDF do leilão. O sistema extrai os dados automaticamente.
2. **Importar Texto:** Cole o texto do e-mail ou WhatsApp e clique em "Processar Texto".
3. **Ajuste Manual:** Confira os dados na tabela. Você pode editar qualquer campo, adicionar novas linhas ou usar as "Ações em Massa" (para preencher data, lote ou estado de várias cédulas de uma vez).
4. **Frete e Custos:** Preencha o valor do frete e (se houver) custos extras. O sistema calculará o rateio automaticamente.
5. **Salvar:** Clique em **"SALVAR LOTE COMPLETO"**.

### Gerando Relatórios (Aba PESQUISAR)
1. Clique em **"Exportar Relatório"**.
2. Escolha o formato **PDF**.
3. Marque o que deseja incluir: Gráfico, Lista de Cédulas e/ou Resumo Financeiro.
4. Clique em **"Baixar Arquivo"**. O PDF será gerado com o gráfico de barras, as bandeiras dos países e a tabela detalhada.

---

## 📂 Estrutura do Projeto

Projeto-final-lp2-Flask/
│
├── app.py                  # Fábrica da aplicação Flask e rotas
├── models.py               # Modelos do banco de dados (SQLAlchemy)
├── dicionario.py           # Dicionário de tradução de estados
├── run.py                  # Ponto de entrada do sistema
├── requirements.txt        # Dependências do projeto
│
├── services/               # Regras de Negócio (Orientação a Objetos)
│   ├── auth_service.py     # Login e criptografia
│   ├── custo_service.py    # Cálculo de rateio de frete
│   ├── pdf_processor.py    # Extração de texto de PDF
│   ├── text_processor.py   # Extração de dados de texto
│   ├── pdf_export_service.py # Geração de relatórios em PDF
│   ├── sistema_service.py  # Backup e restauração
│   └── ...                 # Outros serviços
│
├── templates/              # Templates HTML (Jinja2)
│   ├── login.html
│   ├── cadastro.html
│   └── index.html
│
├── static/                 # Arquivos estáticos
│   ├── img/                # Imagens e logo
│   └── js/                 # Scripts e mapa de bandeiras
│
└── instance/               # Banco de dados SQLite (gerado automaticamente)
    └── cedulas.db

---

## 🧠 Tecnologias Utilizadas

* **Linguagem:** Python 3.10+ e JavaScript
* **Framework Web:** Flask
* **Banco de Dados:** SQLite + SQLAlchemy (ORM)
* **Extração de Dados:** Pdfplumber, Regex
* **Geração de PDF:** ReportLab, Matplotlib, PyPDF2
* **Frontend:** HTML5, CSS3 (Dark Mode), Chart.js (Gráficos)

---

## 👨‍🏫 Créditos Acadêmicos

* **Instituição:** Fatec Rio Claro/SP
* **Curso:** Inteligência Artificial
* **Disciplinas:** Estruturas de Dados / Linguagem de Programação 2
* **Professor:** Orlando Saraiva Jr.
* **Autor do Projeto:** [Seu Nome Aqui] (RA: [Seu RA])
