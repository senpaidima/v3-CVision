from __future__ import annotations

import logging

from openai import AsyncAzureOpenAI

from app.core.config import Settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self) -> None:
        self.client: AsyncAzureOpenAI | None = None
        self.initialized = False
        self.model = ""
        self.dimensions = 0

    async def initialize(self, settings: Settings) -> None:
        if self.initialized:
            return

        if not settings.OPENAI_ENDPOINT or not settings.OPENAI_API_KEY:
            logger.warning("OpenAI credentials missing — EmbeddingService not initialized")
            return

        self.client = AsyncAzureOpenAI(
            azure_endpoint=settings.OPENAI_ENDPOINT,
            api_key=settings.OPENAI_API_KEY,
            api_version=settings.OPENAI_API_VERSION,
        )
        self.model = settings.OPENAI_EMBEDDING_MODEL
        self.dimensions = settings.OPENAI_EMBEDDING_DIMENSIONS
        self.initialized = True

    async def close(self) -> None:
        self.client = None
        self.initialized = False

    async def get_embedding(self, text: str) -> list[float]:
        if not self.initialized or not self.client:
            raise RuntimeError("EmbeddingService not initialized")

        response = await self.client.embeddings.create(
            input=text,
            model=self.model,
            dimensions=self.dimensions,
        )
        return response.data[0].embedding

    async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        if not self.initialized or not self.client:
            raise RuntimeError("EmbeddingService not initialized")

        response = await self.client.embeddings.create(
            input=texts,
            model=self.model,
            dimensions=self.dimensions,
        )
        return [item.embedding for item in response.data]

    async def check_connection(self) -> bool:
        if not self.initialized:
            return False
        try:
            await self.get_embedding("test")
            return True
        except Exception:
            logger.exception("EmbeddingService connection check failed")
            return False


embedding_service = EmbeddingService()
