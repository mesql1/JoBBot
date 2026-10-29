from __future__ import annotations

from jobbot.services.adzuna import AdzunaClient, clean_html, map_job


def test_clean_html_unescapes_entities_and_normalizes_spaces() -> None:
    assert clean_html("<p>Python &amp; Dados</p>\n<b>Remoto</b>") == (
        "Python & Dados Remoto"
    )
    assert clean_html(None) == "Não informado"


def test_map_job_maps_api_fields() -> None:
    job = map_job(
        {
            "id": "123",
            "title": "<strong>Dev Python</strong>",
            "company": {"display_name": "ACME"},
            "location": {"display_name": "São Paulo"},
            "redirect_url": "https://example.test/job/123",
            "description": "APIs &amp; automação",
            "created": "2026-10-29T10:00:00Z",
            "salary_min": 5000,
            "salary_max": 7000,
        },
        "python backend",
    )

    assert job.id == "123"
    assert job.title == "Dev Python"
    assert job.company == "ACME"
    assert job.description == "APIs & automação"
    assert job.created is not None
    assert job.salary_min == 5000
    assert job.term == "python backend"


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    def raise_for_status(self) -> None:
        return None

    async def json(self) -> dict:
        return self.payload


class FakeSession:
    closed = False

    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict]] = []

    def get(self, url: str, *, params: dict):
        self.calls.append((url, params))
        return FakeResponse(self.payload)


async def test_search_uses_quality_filters_and_maps_mocked_api() -> None:
    payload = {
        "results": [
            {
                "id": "abc",
                "title": "Dev",
                "company": {"display_name": "ACME"},
                "location": {"display_name": "Brasil"},
                "redirect_url": "https://example.test/abc",
                "description": "Descrição",
            }
        ]
    }
    session = FakeSession(payload)
    client = AdzunaClient("id", "key")
    client._session = session  # type: ignore[assignment]

    jobs = await client.search("desenvolvedor python", max_days_old=1)

    assert [job.id for job in jobs] == ["abc"]
    _, params = session.calls[0]
    assert params["what"] == "desenvolvedor python"
    assert params["category"] == "it-jobs"
    assert params["sort_by"] == "date"
    assert params["max_days_old"] == 1
