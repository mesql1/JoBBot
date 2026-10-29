from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from typing import Any

import aiohttp

LOGGER = logging.getLogger(__name__)
WHITESPACE_RE = re.compile(r"\s+")
SUPPORTED_COUNTRIES = frozenset(
    {
        "at",
        "au",
        "be",
        "br",
        "ca",
        "ch",
        "de",
        "fr",
        "gb",
        "in",
        "it",
        "nl",
        "nz",
        "pl",
        "sg",
        "us",
        "za",
    }
)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def clean_html(text: str | None) -> str:
    if not text:
        return "Não informado"
    parser = _TextExtractor()
    parser.feed(text)
    parser.close()
    return WHITESPACE_RE.sub(" ", " ".join(parser.parts)).strip()


@dataclass(frozen=True, slots=True)
class Job:
    id: str
    title: str
    company: str
    location: str
    url: str
    description: str
    created: datetime | None
    salary_min: float | None
    salary_max: float | None
    term: str


def map_job(data: dict[str, Any], term: str) -> Job:
    created: datetime | None = None
    if raw_created := data.get("created"):
        try:
            created = datetime.fromisoformat(str(raw_created).replace("Z", "+00:00"))
        except ValueError:
            LOGGER.warning("Data inválida recebida da Adzuna: %s", raw_created)

    company = data.get("company") or {}
    location = data.get("location") or {}
    return Job(
        id=str(data.get("id", "")),
        title=clean_html(data.get("title")),
        company=clean_html(company.get("display_name")),
        location=clean_html(location.get("display_name")),
        url=str(data.get("redirect_url", "")),
        description=clean_html(data.get("description")),
        created=created,
        salary_min=data.get("salary_min"),
        salary_max=data.get("salary_max"),
        term=term,
    )


class AdzunaError(RuntimeError):
    """Falha previsível ao consultar a API da Adzuna."""


class AdzunaClient:
    BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"

    def __init__(
        self,
        app_id: str,
        app_key: str,
        *,
        cache_ttl: float = 300,
        timeout: float = 15,
    ) -> None:
        self.app_id = app_id
        self.app_key = app_key
        self.cache_ttl = cache_ttl
        self.timeout = aiohttp.ClientTimeout(total=timeout, connect=5)
        self._session: aiohttp.ClientSession | None = None
        self._cache: dict[
            tuple[str, str, str, int | None], tuple[float, list[Job]]
        ] = {}
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def search(
        self,
        term: str,
        *,
        location: str | None = None,
        country: str = "br",
        max_days_old: int | None = None,
    ) -> list[Job]:
        normalized = " ".join(term.split()).strip()
        if not normalized:
            return []
        normalized_location = " ".join((location or "").split()).strip()
        country = country.casefold()
        if country not in SUPPORTED_COUNTRIES:
            raise AdzunaError("País não suportado pela Adzuna.")
        cache_key = (
            normalized.casefold(),
            normalized_location.casefold(),
            country,
            max_days_old,
        )
        cached = self._cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < self.cache_ttl:
            return list(cached[1])

        async with self._lock:
            cached = self._cache.get(cache_key)
            if cached and time.monotonic() - cached[0] < self.cache_ttl:
                return list(cached[1])
            jobs = await self._fetch(
                normalized,
                location=normalized_location or None,
                country=country,
                max_days_old=max_days_old,
            )
            self._cache[cache_key] = (time.monotonic(), jobs)
            return list(jobs)

    async def _fetch(
        self,
        term: str,
        *,
        location: str | None,
        country: str,
        max_days_old: int | None,
    ) -> list[Job]:
        await self.start()
        assert self._session is not None
        params: dict[str, str | int] = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "results_per_page": 10,
            "what": term,
            "category": "it-jobs",
            "sort_by": "date",
            "content-type": "application/json",
        }
        if max_days_old is not None:
            params["max_days_old"] = max_days_old
        if location:
            params["where"] = location

        try:
            url = self.BASE_URL.format(country=country)
            async with self._session.get(url, params=params) as response:
                response.raise_for_status()
                payload = await response.json()
        except (TimeoutError, aiohttp.ClientError) as exc:
            raise AdzunaError(
                "A Adzuna não respondeu a tempo. Tente novamente."
            ) from exc

        return [
            map_job(item, term)
            for item in payload.get("results", [])
            if item.get("id") and item.get("redirect_url")
        ]
