from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import aiosqlite

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GuildConfig:
    guild_id: int
    channel_id: int
    terms: tuple[str, ...]
    location: str | None
    country: str


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    async def initialize(self) -> None:
        async with aiosqlite.connect(self.path) as connection:
            await connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS guild_config (
                    guild_id INTEGER PRIMARY KEY,
                    channel_id INTEGER NOT NULL,
                    terms TEXT NOT NULL DEFAULT '["python"]',
                    location TEXT,
                    country TEXT NOT NULL DEFAULT 'br'
                );
                CREATE TABLE IF NOT EXISTS sent_jobs (
                    guild_id INTEGER NOT NULL,
                    job_id TEXT NOT NULL,
                    sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (guild_id, job_id),
                    FOREIGN KEY (guild_id) REFERENCES guild_config(guild_id)
                        ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_sent_jobs_sent_at
                    ON sent_jobs(sent_at);
                """
            )
            cursor = await connection.execute("PRAGMA table_info(guild_config)")
            columns = {row[1] for row in await cursor.fetchall()}
            if "location" not in columns:
                await connection.execute(
                    "ALTER TABLE guild_config ADD COLUMN location TEXT"
                )
            if "country" not in columns:
                await connection.execute(
                    "ALTER TABLE guild_config "
                    "ADD COLUMN country TEXT NOT NULL DEFAULT 'br'"
                )
            await connection.commit()

    async def migrate_json(self, path: Path = Path("servidores.json")) -> None:
        """Importa a configuração antiga uma única vez, quando ela existir."""
        if not path.exists():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            LOGGER.exception("Não foi possível ler a configuração legada %s", path)
            return

        for guild_id, channel_id in raw.items():
            try:
                async with aiosqlite.connect(self.path) as connection:
                    await connection.execute(
                        """
                        INSERT OR IGNORE INTO guild_config
                            (guild_id, channel_id, terms, country)
                        VALUES (?, ?, ?, 'br')
                        """,
                        (int(guild_id), int(channel_id), '["python"]'),
                    )
                    await connection.commit()
            except (TypeError, ValueError):
                LOGGER.warning(
                    "Configuração legada inválida para o servidor %s", guild_id
                )

    async def set_guild(
        self,
        guild_id: int,
        channel_id: int,
        terms: tuple[str, ...],
        location: str | None = None,
        country: str = "br",
    ) -> None:
        async with aiosqlite.connect(self.path) as connection:
            await connection.execute(
                """
                INSERT INTO guild_config
                    (guild_id, channel_id, terms, location, country)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    channel_id = excluded.channel_id,
                    terms = excluded.terms,
                    location = excluded.location,
                    country = excluded.country
                """,
                (
                    guild_id,
                    channel_id,
                    json.dumps(terms, ensure_ascii=False),
                    location,
                    country,
                ),
            )
            await connection.commit()

    async def list_guilds(self) -> list[GuildConfig]:
        async with aiosqlite.connect(self.path) as connection:
            connection.row_factory = aiosqlite.Row
            cursor = await connection.execute(
                """
                SELECT guild_id, channel_id, terms, location, country
                FROM guild_config
                """
            )
            rows = await cursor.fetchall()

        configs: list[GuildConfig] = []
        for row in rows:
            try:
                terms = tuple(json.loads(row["terms"]))
            except (TypeError, json.JSONDecodeError):
                LOGGER.warning("Termos inválidos no servidor %s", row["guild_id"])
                terms = ("python",)
            configs.append(
                GuildConfig(
                    row["guild_id"],
                    row["channel_id"],
                    terms,
                    row["location"],
                    row["country"],
                )
            )
        return configs

    async def unseen_job_ids(self, guild_id: int, job_ids: list[str]) -> set[str]:
        if not job_ids:
            return set()
        placeholders = ",".join("?" for _ in job_ids)
        query = (
            "SELECT job_id FROM sent_jobs "
            f"WHERE guild_id = ? AND job_id IN ({placeholders})"
        )
        async with aiosqlite.connect(self.path) as connection:
            cursor = await connection.execute(query, (guild_id, *job_ids))
            seen = {row[0] for row in await cursor.fetchall()}
        return set(job_ids) - seen

    async def mark_jobs_sent(self, guild_id: int, job_ids: list[str]) -> None:
        async with aiosqlite.connect(self.path) as connection:
            await connection.executemany(
                "INSERT OR IGNORE INTO sent_jobs (guild_id, job_id) VALUES (?, ?)",
                ((guild_id, job_id) for job_id in job_ids),
            )
            await connection.commit()

    async def delete_guild(self, guild_id: int) -> None:
        async with aiosqlite.connect(self.path) as connection:
            await connection.execute(
                "DELETE FROM sent_jobs WHERE guild_id = ?", (guild_id,)
            )
            await connection.execute(
                "DELETE FROM guild_config WHERE guild_id = ?", (guild_id,)
            )
            await connection.commit()
