from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Settings
from app.services.embedding_service import EmbeddingService


def _make_settings() -> Settings:
    return Settings(
        OPENAI_ENDPOINT="https://example.openai.azure.com/",
        OPENAI_API_KEY="test-key",
        OPENAI_API_VERSION="2024-10-21",
        OPENAI_EMBEDDING_MODEL="text-embedding-3-large",
        OPENAI_EMBEDDING_DIMENSIONS=3072,
    )


@pytest.mark.anyio
async def test_get_embedding_returns_vector():
    service = EmbeddingService()
    settings = _make_settings()
    embedding = [0.0] * 3072

    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=embedding)]
    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)

    with patch("app.services.embedding_service.AsyncAzureOpenAI", return_value=mock_client):
        await service.initialize(settings)
        result = await service.get_embedding("hello")

    assert result == embedding
    assert len(result) == 3072


@pytest.mark.anyio
async def test_get_embedding_not_initialized():
    service = EmbeddingService()

    with pytest.raises(RuntimeError):
        await service.get_embedding("hello")


@pytest.mark.anyio
async def test_get_embeddings_batch():
    service = EmbeddingService()
    settings = _make_settings()
    embeddings = [[0.1] * 3072, [0.2] * 3072]

    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(embedding=embeddings[0]),
        MagicMock(embedding=embeddings[1]),
    ]
    mock_client = MagicMock()
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)

    with patch("app.services.embedding_service.AsyncAzureOpenAI", return_value=mock_client):
        await service.initialize(settings)
        result = await service.get_embeddings_batch(["one", "two"])

    assert result == embeddings


@pytest.mark.anyio
async def test_check_connection_success():
    service = EmbeddingService()
    settings = _make_settings()

    with patch("app.services.embedding_service.AsyncAzureOpenAI", return_value=MagicMock()):
        await service.initialize(settings)

    with patch.object(service, "get_embedding", AsyncMock(return_value=[0.0] * 3072)):
        assert await service.check_connection() is True


@pytest.mark.anyio
async def test_check_connection_failure():
    service = EmbeddingService()
    settings = _make_settings()

    with patch("app.services.embedding_service.AsyncAzureOpenAI", return_value=MagicMock()):
        await service.initialize(settings)

    with patch.object(service, "get_embedding", AsyncMock(side_effect=Exception("boom"))):
        assert await service.check_connection() is False
