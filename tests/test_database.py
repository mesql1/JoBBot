from pathlib import Path

from jobbot.database import Database


async def test_database_stores_config_and_deduplicates_jobs(tmp_path: Path) -> None:
    database = Database(tmp_path / "test.db")
    await database.initialize()
    await database.set_guild(10, 20, ("python", "dados"), "São Paulo", "br")

    configs = await database.list_guilds()
    assert len(configs) == 1
    assert configs[0].terms == ("python", "dados")
    assert configs[0].location == "São Paulo"
    assert configs[0].country == "br"
    assert await database.unseen_job_ids(10, ["a", "b"]) == {"a", "b"}

    await database.mark_jobs_sent(10, ["a"])
    assert await database.unseen_job_ids(10, ["a", "b"]) == {"b"}

    await database.delete_guild(10)
    assert await database.list_guilds() == []
