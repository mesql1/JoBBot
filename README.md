# JoBBot — monitor de vagas de TI para Discord

JoBBot busca oportunidades na Adzuna, publica apenas vagas novas diariamente e
permite buscas sob demanda por slash commands. Cada servidor escolhe seu canal e
até cinco termos de busca.

## O que o bot oferece

- busca assíncrona, com timeout e cache curto para não bloquear o Discord nem
  desperdiçar a cota da Adzuna;
- publicação diária às **09:00 no horário de São Paulo**;
- filtro de categoria de TI, ordenação por data e vagas das últimas 24 horas;
- deduplicação por ID da Adzuna, persistida em SQLite;
- até dez embeds por mensagem, com empresa, local, salário, data e descrição;
- isolamento de falhas por servidor: um canal sem permissão não interrompe os
  demais;
- slash commands, sem necessidade da intent privilegiada `message_content`.

## Pré-requisitos

- Python 3.12 ou Docker;
- uma aplicação no [Discord Developer Portal](https://discord.com/developers/applications);
- credenciais no [Adzuna Developer Portal](https://developer.adzuna.com/).

No portal do Discord, adicione um bot à aplicação. Nenhuma intent privilegiada é
necessária. Na página **OAuth2 > URL Generator**, selecione os escopos `bot` e
`applications.commands` e dê ao bot as permissões View Channels, Send Messages,
Embed Links e Read Message History. Você também pode substituir `SEU_CLIENT_ID`
neste link:

```text
https://discord.com/oauth2/authorize?client_id=SEU_CLIENT_ID&scope=bot%20applications.commands&permissions=84992
```

## Instalação local

Clone o projeto e entre na pasta:

```bash
git clone https://github.com/mesql1/JoBBot.git
cd JoBBot
python -m venv .venv
```

Ative o ambiente no Windows (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
```

No Linux ou macOS:

```bash
source .venv/bin/activate
```

Instale e configure:

```bash
pip install -r requirements.txt
cp .env.example .env  # no Windows: Copy-Item .env.example .env
```

Preencha `DISCORD_TOKEN`, `ADZUNA_ID` e `ADZUNA_KEY` no `.env`. Para testar os
comandos imediatamente em um servidor, informe também seu ID em
`DISCORD_GUILD_ID`. Sem essa variável, os comandos são globais e o Discord pode
levar algum tempo para propagá-los.

Não é necessário criar `servidores.json`: o banco `jobbot.db` é criado
automaticamente. Se uma instalação antiga tiver `servidores.json`, os canais são
importados ao iniciar.

Execute:

```bash
python main.py
```

O processo falha cedo e informa quais variáveis obrigatórias estão faltando.

## Comandos

- `/oi`: confirma que o bot está online;
- `/buscar termo:"desenvolvedor python"`: pesquisa uma expressão completa. Cada
  usuário pode fazer duas buscas por minuto;
- `/setar_canal canal:#vagas termos:"python, dados, suporte"`: configura o canal
  e de um a cinco termos. Requer permissão de administrador.

## Hospedagem 24/7

### Docker

```bash
docker build -t jobbot .
docker run --env-file .env -v jobbot-data:/app/data \
  -e DATABASE_PATH=/app/data/jobbot.db jobbot
```

Em um VPS, use o mesmo container com uma política de reinício, por exemplo
`--restart unless-stopped`. No Railway ou serviço semelhante, conecte o
repositório, cadastre as três variáveis secretas e anexe um volume persistente;
aponte `DATABASE_PATH` para esse volume. Sem disco persistente, o histórico de
deduplicação será perdido a cada deploy.

## Desenvolvimento

```bash
pip install -r requirements-dev.txt
ruff check .
ruff format --check .
pytest
```

O workflow em `.github/workflows/ci.yml` executa lint, formatação e testes em
pushes e pull requests. Os testes cobrem limpeza de HTML, mapeamento de uma
resposta simulada da Adzuna e persistência/deduplicação no SQLite.

## Estrutura

```text
main.py                    ponto de entrada e logging
jobbot/bot.py              ciclo de vida do bot
jobbot/cogs/jobs.py        comandos e tarefa agendada
jobbot/services/adzuna.py  cliente HTTP, cache e mapeamento
jobbot/database.py         configurações e IDs enviados no SQLite
jobbot/embeds.py           apresentação das vagas
tests/                     testes automatizados
```

## Licença

[MIT](LICENSE)
