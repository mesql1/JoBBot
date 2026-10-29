from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    discord_token: str
    adzuna_id: str
    adzuna_key: str
    database_path: Path
    discord_guild_id: int | None = None

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        required = {
            "DISCORD_TOKEN": os.getenv("DISCORD_TOKEN"),
            "ADZUNA_ID": os.getenv("ADZUNA_ID"),
            "ADZUNA_KEY": os.getenv("ADZUNA_KEY"),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            names = ", ".join(missing)
            raise RuntimeError(f"Variáveis de ambiente obrigatórias ausentes: {names}")

        guild_id = os.getenv("DISCORD_GUILD_ID")
        try:
            parsed_guild_id = int(guild_id) if guild_id else None
        except ValueError as exc:
            raise RuntimeError("DISCORD_GUILD_ID deve ser um número inteiro") from exc

        return cls(
            discord_token=required["DISCORD_TOKEN"] or "",
            adzuna_id=required["ADZUNA_ID"] or "",
            adzuna_key=required["ADZUNA_KEY"] or "",
            database_path=Path(os.getenv("DATABASE_PATH", "jobbot.db")),
            discord_guild_id=parsed_guild_id,
        )
