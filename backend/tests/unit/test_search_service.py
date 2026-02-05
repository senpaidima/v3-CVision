from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.services.search_service import SearchService


def _make_settings() -> Settings:
    return Settings(
        AZURE_SEARCH_ENDPOINT="https://example.search.windows.net",
        AZURE_SEARCH_KEY="test-key",
        AZURE_SEARCH_INDEX="cvision-v3-index",
        AZURE_SEARCH_API_VERSION="2024-07-01",
    )


def _mock_session(response: MagicMock) -> MagicMock:
    mock_post_context = AsyncMock()
    mock_post_context.__aenter__.return_value = response
    mock_post_context.__aexit__.return_value = None

    session = MagicMock()
    session.post.return_value = mock_post_context
    session.get.return_value = mock_post_context
    return session


def _mock_client_session(session: MagicMock) -> AsyncMock:
    mock_client_session = AsyncMock()
    mock_client_session.__aenter__.return_value = session
    mock_client_session.__aexit__.return_value = None
    return mock_client_session


@pytest.mark.anyio
async def test_hybrid_search_returns_results():
    service = SearchService()
    settings = _make_settings()

    search_data = {
        "value": [
            {
                "id": "1",
                "employeeName": "Jane Doe",
                "employeeAlias": "JDOE",
                "content": "Sample content",
                "skills": ["Python"],
                "tools": ["FastAPI"],
                "title": "Engineer",
                "location": "Berlin",
                "@search.score": 1.23,
            }
        ]
    }

    response = MagicMock()
    response.status = 200
    response.json = AsyncMock(return_value=search_data)

    session = _mock_session(response)
    mock_client_session = _mock_client_session(session)

    with patch("app.services.search_service.aiohttp.ClientSession", return_value=mock_client_session):
        await service.initialize(settings)
        results = await service.hybrid_search("python")

    assert len(results) == 1
    assert results[0]["employee_name"] == "Jane Doe"
    assert results[0]["employee_alias"] == "JDOE"


@pytest.mark.anyio
async def test_hybrid_search_with_vector():
    service = SearchService()
    settings = _make_settings()

    response = MagicMock()
    response.status = 200
    response.json = AsyncMock(return_value={"value": []})

    session = _mock_session(response)
    mock_client_session = _mock_client_session(session)

    with patch("app.services.search_service.aiohttp.ClientSession", return_value=mock_client_session):
        await service.initialize(settings)
        await service.hybrid_search("python", query_vector=[0.1, 0.2, 0.3])

    payload = session.post.call_args.kwargs["json"]
    assert "vectorQueries" in payload
    assert payload["vectorQueries"][0]["fields"] == "contentVector"


@pytest.mark.anyio
async def test_hybrid_search_with_filters():
    service = SearchService()
    settings = _make_settings()

    response = MagicMock()
    response.status = 200
    response.json = AsyncMock(return_value={"value": []})

    session = _mock_session(response)
    mock_client_session = _mock_client_session(session)

    with patch("app.services.search_service.aiohttp.ClientSession", return_value=mock_client_session):
        await service.initialize(settings)
        await service.hybrid_search("python", filters="location eq 'Berlin'")

    payload = session.post.call_args.kwargs["json"]
    assert payload["filter"] == "location eq 'Berlin'"


def test_process_results():
    service = SearchService()
    data = {
        "value": [
            {
                "id": "2",
                "employeeName": "John Smith",
                "employeeAlias": "JSMI",
                "content": "X" * 800,
                "skills": ["Azure"],
                "tools": ["Azure Search"],
                "title": "Consultant",
                "location": "Munich",
                "@search.score": 2.5,
            }
        ]
    }

    results = service._process_results(data)
    assert results[0]["id"] == "2"
    assert results[0]["employee_name"] == "John Smith"
    assert len(results[0]["content"]) == 500


@pytest.mark.anyio
async def test_search_not_initialized():
    service = SearchService()

    with pytest.raises(RuntimeError):
        await service.hybrid_search("python")
