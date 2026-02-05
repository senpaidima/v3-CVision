from __future__ import annotations

import copy
import logging

import aiohttp

from app.core.config import Settings

logger = logging.getLogger(__name__)


INDEX_SCHEMA: dict[str, object] = {
    "name": "cvision-v3-index",
    "fields": [
        {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
        {
            "name": "employeeName",
            "type": "Edm.String",
            "searchable": True,
            "filterable": True,
            "sortable": True,
        },
        {"name": "employeeAlias", "type": "Edm.String", "filterable": True},
        {"name": "content", "type": "Edm.String", "searchable": True},
        {
            "name": "skills",
            "type": "Collection(Edm.String)",
            "searchable": True,
            "filterable": True,
        },
        {
            "name": "tools",
            "type": "Collection(Edm.String)",
            "searchable": True,
            "filterable": True,
        },
        {"name": "experience", "type": "Edm.String", "searchable": True},
        {"name": "projects", "type": "Edm.String", "searchable": True},
        {
            "name": "title",
            "type": "Edm.String",
            "searchable": True,
            "filterable": True,
        },
        {
            "name": "location",
            "type": "Edm.String",
            "filterable": True,
            "sortable": True,
        },
        {"name": "department", "type": "Edm.String", "filterable": True},
        {
            "name": "yearsOfExperience",
            "type": "Edm.Double",
            "filterable": True,
            "sortable": True,
        },
        {
            "name": "contentVector",
            "type": "Collection(Edm.Single)",
            "searchable": True,
            "dimensions": 3072,
            "vectorSearchProfile": "default-profile",
        },
    ],
    "vectorSearch": {
        "algorithms": [
            {
                "name": "default-hnsw",
                "kind": "hnsw",
                "hnswParameters": {
                    "m": 4,
                    "efConstruction": 400,
                    "efSearch": 500,
                    "metric": "cosine",
                },
            }
        ],
        "profiles": [{"name": "default-profile", "algorithm": "default-hnsw"}],
    },
}


async def create_or_update_index(settings: Settings) -> bool:
    """Create or update the Azure AI Search index via REST API."""
    endpoint = settings.AZURE_SEARCH_ENDPOINT.rstrip("/")
    api_key = settings.AZURE_SEARCH_KEY
    api_version = settings.AZURE_SEARCH_API_VERSION

    if not endpoint or not api_key:
        logger.warning("Azure Search credentials missing — index not created")
        return False

    index_name = settings.AZURE_SEARCH_INDEX or INDEX_SCHEMA["name"]
    payload = copy.deepcopy(INDEX_SCHEMA)
    payload["name"] = index_name

    fields = payload.get("fields")
    if isinstance(fields, list):
        for field in fields:
            if field.get("name") == "contentVector":
                field["dimensions"] = settings.OPENAI_EMBEDDING_DIMENSIONS
                break

    url = f"{endpoint}/indexes/{index_name}?api-version={api_version}"
    headers = {"Content-Type": "application/json", "api-key": api_key}

    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.put(url, headers=headers, json=payload) as response:
                if response.status in (200, 201):
                    logger.info("Search index created/updated: %s", index_name)
                    return True

                error_text = await response.text()
                logger.error(
                    "Search index creation failed (%s): %s",
                    response.status,
                    error_text,
                )
                return False
    except Exception:
        logger.exception("Search index creation failed")
        return False
