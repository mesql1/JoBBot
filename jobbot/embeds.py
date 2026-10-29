from __future__ import annotations

import discord

from jobbot.services.adzuna import Job


def _brl(value: float) -> str:
    formatted = f"{value:,.0f}".replace(",", ".")
    return f"R$ {formatted}"


def _salary(job: Job) -> str:
    if job.salary_min is None and job.salary_max is None:
        return "Não informado"
    if job.salary_min is not None and job.salary_max is not None:
        return f"{_brl(job.salary_min)} – {_brl(job.salary_max)}"
    value = job.salary_min if job.salary_min is not None else job.salary_max
    return _brl(value) if value is not None else "Não informado"


def job_embed(job: Job, *, automatic: bool = False) -> discord.Embed:
    description = job.description
    if len(description) > 350:
        description = f"{description[:347].rstrip()}..."
    embed = discord.Embed(
        title=job.title[:256],
        url=job.url,
        description=description,
        color=discord.Color.green() if automatic else discord.Color.blue(),
    )
    embed.add_field(name="Empresa", value=job.company[:1024], inline=True)
    embed.add_field(name="Localização", value=job.location[:1024], inline=True)
    embed.add_field(name="Salário", value=_salary(job), inline=True)
    if job.created:
        embed.add_field(
            name="Publicada em",
            value=discord.utils.format_dt(job.created, style="D"),
            inline=True,
        )
    embed.add_field(name="Busca", value=job.term[:1024], inline=True)
    footer = "Busca automática diária" if automatic else "Busca sob demanda"
    embed.set_footer(text=f"{footer} • Fonte: Adzuna Jobs")
    return embed
