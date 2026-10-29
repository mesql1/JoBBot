from __future__ import annotations

import logging

import discord
from discord.ext import commands

from jobbot.database import Database
from jobbot.services.adzuna import AdzunaClient
from jobbot.settings import Settings

LOGGER = logging.getLogger(__name__)


class JobBot(commands.Bot):
    database: Database
    adzuna: AdzunaClient

    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.settings = settings
        self.database = Database(settings.database_path)
        self.adzuna = AdzunaClient(settings.adzuna_id, settings.adzuna_key)

    async def setup_hook(self) -> None:
        await self.database.initialize()
        await self.database.migrate_json()
        await self.adzuna.start()
        await self.load_extension("jobbot.cogs.jobs")

        if self.settings.discord_guild_id:
            guild = discord.Object(id=self.settings.discord_guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            LOGGER.info(
                "%d comandos sincronizados no servidor de desenvolvimento", len(synced)
            )
        else:
            synced = await self.tree.sync()
            LOGGER.info("%d comandos globais sincronizados", len(synced))

    async def close(self) -> None:
        await self.adzuna.close()
        await super().close()

    async def on_ready(self) -> None:
        LOGGER.info(
            "Bot conectado como %s (%s)", self.user, self.user.id if self.user else "?"
        )

    async def on_guild_remove(self, guild: discord.Guild) -> None:
        await self.database.delete_guild(guild.id)
        LOGGER.info("Configuração removida para o servidor %s", guild.id)
