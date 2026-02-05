from __future__ import annotations

import logging

import aiohttp

from app.core.config import Settings

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(self) -> None:
        self.initialized = False
        self.endpoint = ""
        self.api_key = ""
        self.index_name = ""
        self.api_version = ""

    async def initialize(self, settings: Settings) -> None:
        if self.initialized:
            return

        if not settings.AZURE_SEARCH_ENDPOINT or not settings.AZURE_SEARCH_KEY:
            logger.warning("Azure Search credentials missing — SearchService not initialized")
            return

        self.endpoint = settings.AZURE_SEARCH_ENDPOINT.rstrip("/")
        self.api_key = settings.AZURE_SEARCH_KEY
        self.index_name = settings.AZURE_SEARCH_INDEX
        self.api_version = settings.AZURE_SEARCH_API_VERSION
        self.initialized = True

    async def close(self) -> None:
        self.initialized = False
        self.endpoint = ""
        self.api_key = ""
        self.index_name = ""
        self.api_version = ""

    async def hybrid_search(
        self,
        query_text: str,
        query_vector: list[float] | None = None,
        top: int = 10,
        filters: str | None = None,
    ) -> list[dict]:
        if not self.initialized:
            raise RuntimeError("SearchService not initialized")

        search_text = query_text.strip() if query_text.strip() else "*"
        payload: dict[str, object] = {
            "search": search_text,
            "select": (
                "id,employeeName,employeeAlias,content,skills,tools,title,location,department,yearsOfExperience"
            ),
            "top": top,
            "queryType": "full",
        }

        if query_vector:
            payload["vectorQueries"] = [
                {
                    "kind": "vector",
                    "vector": query_vector,
                    "fields": "contentVector",
                    "k": top * 2,
                    "exhaustive": True,
                }
            ]

        if filters:
            payload["filter"] = filters

        url = f"{self.endpoint}/indexes/{self.index_name}/docs/search?api-version={self.api_version}"
        headers = {"Content-Type": "application/json", "api-key": self.api_key}

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._process_results(data)

                error_text = await response.text()
                raise RuntimeError(f"Search failed: {response.status} - {error_text}")

    def _process_results(self, data: dict) -> list[dict]:
        results: list[dict] = []
        for doc in data.get("value", []):
            results.append(
                {
                    "id": doc.get("id"),
                    "employee_name": doc.get("employeeName"),
                    "employee_alias": doc.get("employeeAlias"),
                    "content": doc.get("content", "")[:500],
                    "skills": doc.get("skills", []),
                    "tools": doc.get("tools", []),
                    "title": doc.get("title"),
                    "location": doc.get("location"),
                    "score": doc.get("@search.score", 0),
                }
            )
        return results

    async def check_connection(self) -> bool:
        if not self.initialized:
            return False

        url = f"{self.endpoint}/indexes/{self.index_name}?api-version={self.api_version}"
        headers = {"Content-Type": "application/json", "api-key": self.api_key}

        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    return response.status == 200
        except Exception:
            logger.exception("SearchService connection check failed")
            return False


search_service = SearchService()
