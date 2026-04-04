from discord.ext import tasks,commands
from vagas_api import buscar_vagasOnline
import discord
import os
from dotenv import load_dotenv
import json

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()
TOKEN=os.getenv('DISCORD_TOKEN') # Obtém o token do bot a partir das variáveis de ambiente

intents=discord.Intents.default()# Cria uma instância de Intents para configurar as permissões do bot
intents.message_content=True# Habilita a permissão para ler o conteúdo das mensagens

bot=commands.Bot(command_prefix="!", intents=intents) # Cria uma instância do bot com o prefixo de comando "!" e as intenções configuradas

@bot.event # Define um evento para quando o bot estiver pronto
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    tarefa_vagas.start()  # Inicia a tarefa de busca de vagas

def load_config():
    try:
        with open('servidores.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}  # Retorna um dicionário vazio se o arquivo não existir ou estiver corrompido

@bot.command()
@commands.has_permissions(administrator=True)  # Restringe o comando para administradores
async def setar_canal(ctx):
    with open('servidores.json','r') as f:
        config=json.load(f)
    
    config[str(ctx.guild.id)]=ctx.channel.id

    with open('servidores.json','w') as f:
        json.dump(config,f,indent=4)

    await ctx.send(f'Canal de vagas atualizado para {ctx.channel.mention}.')

@tasks.loop(hours=24)  # Executa a cada 24 horas
async def tarefa_vagas():
    with open('servidores.json','r') as f:
        config=json.load(f)
    
    vagas=buscar_vagasOnline("TI")  # Busca as vagas online

    for guild_id, canal_id in config.items():
        canal=bot.get_channel(int(canal_id))
        if canal:
            for vaga in vagas:
                titulo=vaga.get("titulo", "N/A")
                localizacao=vaga.get("localizacao", "Remoto/Não informado.")
                link=vaga.get("link", "N/A")
                area=vaga.get("area", "N/A")

                embed=discord.Embed(
                    title=titulo,
                    url=link,
                    description=f"Oportunidade para {area.upper()}",
                    color=discord.Color.green()
                )
                embed.add_field(name="Localização", value=localizacao, inline=True)
                embed.set_footer(text="Busca automática diária - Fonte: Adzuna Jobs")

                await canal.send(embed=embed)  # Envia a mensagem para o canal

@bot.command()
async def oi(ctx):
    await ctx.send(f'Olá {ctx.author.name}! Eu estou funcionando!')

@bot.command()
async def buscar(ctx,termo="python"):
    await ctx.send(f'Buscando vagas para {termo}...')

    vagas=buscar_vagasOnline(termo)

    if not vagas:
        await ctx.send(f'Nenhuma vaga encontrada para {termo}.')
        return
    
    for vaga in vagas:
        embed=discord.Embed(
            title=vaga.get('titulo'),
            url=vaga.get('link'),
            description=f"Oportunidade para {termo.upper()}",
            color=discord.Color.blue()
        )

        embed.add_field(name="Empresa",value=vaga.get('empresa'),inline=True)
        embed.add_field(name="Localização",value=vaga.get('localizacao'),inline=True)
        embed.set_footer(text="Fonte: Adzuna Jobs")

        await ctx.send(embed=embed)

bot.run(os.getenv('DISCORD_TOKEN'))  # Inicia o bot usando o token do ambiente