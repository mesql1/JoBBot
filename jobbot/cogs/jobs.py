from __future__ import annotations

import logging
from datetime import time
from itertools import islice
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks

from jobbot.database import GuildConfig
from jobbot.embeds import job_embed
from jobbot.services.adzuna import AdzunaError, Job

LOGGER = logging.getLogger(__name__)
SAO_PAULO = ZoneInfo("America/Sao_Paulo")
DEFAULT_TERMS = ("python",)


def batches(items: list[Job], size: int = 10):
    iterator = iter(items)
    while batch := list(islice(iterator, size)):
        yield batch


class JobsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        if not self.daily_jobs.is_running():
            self.daily_jobs.start()

    def cog_unload(self) -> None:
        self.daily_jobs.cancel()

    @app_commands.command(name="oi", description="Confirma que o JoBBot está online.")
    async def hello(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            f"Olá, {interaction.user.mention}! Eu estou funcionando.", ephemeral=True
        )

    @app_commands.command(
        name="setar_canal",
        description="Define onde e para quais termos as vagas diárias serão enviadas.",
    )
    @app_commands.describe(
        canal="Canal de destino (por padrão, o canal atual)",
        termos="Termos separados por vírgula, por exemplo: python, dados, suporte",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def set_channel(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel | None = None,
        termos: str = "python",
    ) -> None:
        if interaction.guild_id is None:
            await interaction.response.send_message(
                "Este comando só pode ser usado em um servidor.", ephemeral=True
            )
            return
        selected_channel = canal or interaction.channel
        if not isinstance(selected_channel, discord.TextChannel):
            await interaction.response.send_message(
                "Escolha um canal de texto do servidor.", ephemeral=True
            )
            return

        parsed_terms = tuple(
            dict.fromkeys(term.strip() for term in termos.split(",") if term.strip())
        )
        if not parsed_terms or len(parsed_terms) > 5:
            await interaction.response.send_message(
                "Informe de 1 a 5 termos separados por vírgula.", ephemeral=True
            )
            return
        if any(len(term) > 50 for term in parsed_terms):
            await interaction.response.send_message(
                "Cada termo pode ter no máximo 50 caracteres.", ephemeral=True
            )
            return

        await self.bot.database.set_guild(
            interaction.guild_id, selected_channel.id, parsed_terms
        )
        readable_terms = ", ".join(f"`{term}`" for term in parsed_terms)
        message = (
            f"Canal atualizado para {selected_channel.mention}. "
            f"Buscas: {readable_terms}."
        )
        await interaction.response.send_message(
            message,
            ephemeral=True,
        )

    @set_channel.error
    async def set_channel_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            message = "Apenas administradores podem configurar o canal."
        else:
            LOGGER.exception("Erro no comando /setar_canal", exc_info=error)
            message = "Não foi possível salvar a configuração. Tente novamente."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="buscar", description="Busca vagas recentes na Adzuna.")
    @app_commands.describe(termo="Tecnologia, cargo ou expressão que deseja buscar")
    @app_commands.checks.cooldown(
        2, 60.0, key=lambda interaction: (interaction.guild_id, interaction.user.id)
    )
    async def search(
        self, interaction: discord.Interaction, termo: str = "python"
    ) -> None:
        termo = " ".join(termo.split()).strip()
        if not termo or len(termo) > 100:
            await interaction.response.send_message(
                "Use um termo de busca com até 100 caracteres.", ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)
        try:
            jobs = await self.bot.adzuna.search(termo)
        except AdzunaError as exc:
            await interaction.followup.send(str(exc), ephemeral=True)
            return

        if not jobs:
            await interaction.followup.send(
                f"Nenhuma vaga encontrada para **{termo}**.", ephemeral=True
            )
            return
        for index, batch in enumerate(batches(jobs)):
            await interaction.followup.send(
                content=f"Vagas para **{termo}**:" if index == 0 else None,
                embeds=[job_embed(job) for job in batch],
            )

    @search.error
    async def search_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.CommandOnCooldown):
            message = f"Aguarde {error.retry_after:.0f}s antes de buscar novamente."
        else:
            LOGGER.exception("Erro no comando /buscar", exc_info=error)
            message = "A busca falhou inesperadamente. Tente novamente."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    @tasks.loop(time=time(hour=9, tzinfo=SAO_PAULO))
    async def daily_jobs(self) -> None:
        for config in await self.bot.database.list_guilds():
            try:
                await self._send_for_guild(config)
            except discord.Forbidden:
                LOGGER.error(
                    "Sem permissão para enviar vagas no canal %s do servidor %s",
                    config.channel_id,
                    config.guild_id,
                )
            except discord.HTTPException:
                LOGGER.exception(
                    "O Discord rejeitou o envio ao servidor %s", config.guild_id
                )
            except Exception:
                LOGGER.exception(
                    "Falha isolada ao processar o servidor %s", config.guild_id
                )

    async def _send_for_guild(self, config: GuildConfig) -> None:
        channel = self.bot.get_channel(config.channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(config.channel_id)
            except (discord.NotFound, discord.Forbidden):
                LOGGER.warning("Canal %s não está acessível", config.channel_id)
                return
        if not isinstance(channel, discord.TextChannel):
            LOGGER.warning("Canal %s não é um canal de texto", config.channel_id)
            return

        unique_jobs: dict[str, Job] = {}
        for term in config.terms or DEFAULT_TERMS:
            try:
                for job in await self.bot.adzuna.search(term, max_days_old=1):
                    unique_jobs.setdefault(job.id, job)
            except AdzunaError:
                LOGGER.exception(
                    "Falha na busca %r para o servidor %s", term, config.guild_id
                )

        unseen = await self.bot.database.unseen_job_ids(
            config.guild_id, list(unique_jobs)
        )
        jobs = [job for job_id, job in unique_jobs.items() if job_id in unseen]
        jobs.sort(
            key=lambda job: job.created.timestamp() if job.created else 0,
            reverse=True,
        )

        for batch in batches(jobs):
            await channel.send(embeds=[job_embed(job, automatic=True) for job in batch])
            await self.bot.database.mark_jobs_sent(
                config.guild_id, [job.id for job in batch]
            )

    @daily_jobs.before_loop
    async def before_daily_jobs(self) -> None:
        await self.bot.wait_until_ready()

    @daily_jobs.error
    async def daily_jobs_error(self, error: BaseException) -> None:
        LOGGER.critical("A tarefa diária foi encerrada", exc_info=error)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(JobsCog(bot))
