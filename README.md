# JoBBot 🚀 - Monitor de Vagas de TI

O JoBBot é um bot para Discord desenvolvido em Python que automatiza a busca de oportunidades de emprego na área de Tecnologia. Ele utiliza a API da Adzuna para buscar dados em tempo real e permite que diferentes servidores configurem seus próprios canais de anúncio.

# ✨ Funcionalidades
Busca Automática: Envia uma lista de vagas de TI a cada 24 horas em canais configurados.

Busca Manual: Comando !buscar [termo] para pesquisar tecnologias específicas (ex: !buscar react).

Interface Amigável: Exibição das vagas utilizando Discord Embeds para melhor leitura e links diretos.

Segurança: Gestão de credenciais através de variáveis de ambiente (.env).

# 🛠️ Tecnologias Utilizadas
Python 3.12

discord.py: Integração com a API do Discord.

Requests: Consumo da API REST da Adzuna.

python-dotenv: Gerenciamento de chaves de API e tokens.

JSON: Persistência local de configurações dos servidores.

# 🚀 Como Executar o Projeto
1. Pré-requisitos:

Ter o Python instalado.

Criar uma aplicação no Discord Developer Portal.

Obter uma App ID e App Key no Adzuna Developer Portal.

2. Instalação

Clone o repositório e acesse a pasta:

Bash
git clone https://github.com/seu-usuario/jobbot.git

cd jobbot

Crie e ative um ambiente virtual:

python -m venv venv
# Windows:
.\venv\Scripts\activate
Instale as dependências:

Bash
pip install -r requirements.txt
3. Configuração
Crie um arquivo .env na raiz do projeto e adicione suas credenciais:

DISCORD_TOKEN=seu_token_aqui

ADZUNA_ID=seu_id_aqui

ADZUNA_KEY=sua_chave_aqui

Certifique-se de criar um arquivo servidores.json inicial com apenas {} dentro.

4. Rodando o Bot

python main.py

# 📂 Estrutura do Projeto

main.py: Coração do bot, gerencia eventos, comandos e o loop de automação.

vagas_api.py: Módulo responsável pela comunicação com a API da Adzuna e tratamento de dados (limpeza de HTML e mapeamento de JSON).

.env: (Não incluído no repo) Armazena chaves sensíveis.

servidores.json: (Não incluído no repo) Armazena a configuração de canais por servidor.

📝 Comandos

!oi: Verifica se o bot está online.

!setar_canal: Define o canal atual como o destino das vagas automáticas (Requer Admin).

!buscar [termo]: Busca vagas em tempo real sobre um tema específico.