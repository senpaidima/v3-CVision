#!/usr/bin/env python3
"""One-time re-indexing script for cvision-v3-index.

BLOCKER: text-embedding-3-large is NOT yet deployed to Azure OpenAI.
This script will fail at the embedding step until the model is provisioned.
Once deployed, run from the backend/ directory:

    python3 scripts/reindex.py [--dry-run] [--batch-size N] [--verbose]

Reads ALL employees from Cosmos DB (read-only), generates embeddings,
and uploads search documents to the cvision-v3-index Azure AI Search index.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Any

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import aiohttp  # noqa: E402
from azure.cosmos.aio import CosmosClient  # noqa: E402
from openai import AsyncAzureOpenAI  # noqa: E402

from app.core.config import Settings  # noqa: E402

logger = logging.getLogger(__name__)


def _calculate_years(start_date: str | None) -> float:
    if not start_date:
        return 0.0
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            start = datetime.strptime(start_date, fmt)  # noqa: DTZ007
            years = (datetime.now() - start).days / 365.25  # noqa: DTZ005
            return round(years, 1)
        except ValueError:
            continue
    return 0.0


def build_searchable_text(doc: dict[str, Any]) -> str:
    """Build searchable text from a Cosmos DB employee document.

    Cosmos DB fields use space-separated names ("First Name", "Job Title").
    This function concatenates key fields into a single string for embedding.
    """
    parts: list[str] = []

    name = doc.get("Employee", "")
    if name:
        parts.append(f"Name: {name}")

    title = doc.get("Job Title") or doc.get("New Job Title", "")
    if title:
        parts.append(f"Title: {title}")

    skills = doc.get("Skills", [])
    if isinstance(skills, list) and skills:
        parts.append(f"Skills: {', '.join(str(s) for s in skills)}")
    elif isinstance(skills, str) and skills:
        parts.append(f"Skills: {skills}")

    tools = doc.get("Tools", [])
    if isinstance(tools, list) and tools:
        parts.append(f"Tools: {', '.join(str(t) for t in tools)}")
    elif isinstance(tools, str) and tools:
        parts.append(f"Tools: {tools}")

    experience = doc.get("Experience", "")
    if experience:
        parts.append(f"Experience: {experience}")

    projects = doc.get("Projects", "")
    if projects:
        parts.append(f"Projects: {projects}")

    department = doc.get("Department", "")
    if department:
        parts.append(f"Department: {department}")

    location = doc.get("Location", "")
    if location:
        parts.append(f"Location: {location}")

    return "\n".join(parts)


def build_search_document(doc: dict[str, Any], embedding: list[float]) -> dict[str, Any]:
    """Map Cosmos DB employee doc (space-separated keys) to camelCase search index fields."""
    alias = doc.get("Alias") or doc.get("id") or "unknown"
    name = doc.get("Employee", "")
    title = doc.get("Job Title") or doc.get("New Job Title", "")

    skills = doc.get("Skills", [])
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]

    tools = doc.get("Tools", [])
    if isinstance(tools, str):
        tools = [t.strip() for t in tools.split(",") if t.strip()]

    return {
        "@search.action": "mergeOrUpload",
        "id": alias,
        "employeeName": name,
        "employeeAlias": alias,
        "content": build_searchable_text(doc),
        "skills": skills if isinstance(skills, list) else [],
        "tools": tools if isinstance(tools, list) else [],
        "experience": doc.get("Experience", ""),
        "projects": doc.get("Projects", ""),
        "title": title,
        "location": doc.get("Location", ""),
        "department": doc.get("Department", ""),
        "yearsOfExperience": _calculate_years(doc.get("Start")),
        "contentVector": embedding,
    }


async def upload_batch(
    session: aiohttp.ClientSession,
    url: str,
    headers: dict[str, str],
    documents: list[dict[str, Any]],
    *,
    dry_run: bool = False,
) -> tuple[int, int]:
    if dry_run:
        return len(documents), 0

    payload = {"value": documents}
    async with session.post(url, headers=headers, json=payload) as response:
        if response.status in (200, 207):
            data = await response.json()
            results = data.get("value", [])
            succeeded = sum(1 for r in results if r.get("status") is True or r.get("statusCode") in (200, 201))
            return succeeded, len(results) - succeeded

        error = await response.text()
        raise RuntimeError(f"Upload failed ({response.status}): {error}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Re-index all employees into Azure AI Search (cvision-v3-index)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build documents without uploading (skip embeddings and search upload)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of employees per batch (default: 10)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging",
    )
    return parser.parse_args(argv)


async def reindex(args: argparse.Namespace) -> None:
    settings = Settings()
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")

    logger.info("Connecting to Cosmos DB...")
    cosmos_client = CosmosClient(settings.COSMOS_DB_ENDPOINT, settings.COSMOS_DB_KEY)
    try:
        db = cosmos_client.get_database_client(settings.COSMOS_DB_DATABASE)
        container = db.get_container_client(settings.COSMOS_DB_EMPLOYEES_CONTAINER)

        logger.info("Fetching all employees...")
        employees: list[dict[str, Any]] = []
        async for item in container.read_all_items():
            employees.append(item)

        logger.info("Found %d employees", len(employees))
        if not employees:
            logger.warning("No employees found. Exiting.")
            return

        openai_client: AsyncAzureOpenAI | None = None
        if not args.dry_run:
            logger.info("Initializing OpenAI embedding client...")
            openai_client = AsyncAzureOpenAI(
                azure_endpoint=settings.OPENAI_ENDPOINT,
                api_key=settings.OPENAI_API_KEY,
                api_version=settings.OPENAI_API_VERSION,
            )

        search_url = (
            f"{settings.AZURE_SEARCH_ENDPOINT.rstrip('/')}/indexes/"
            f"{settings.AZURE_SEARCH_INDEX}/docs/index"
            f"?api-version={settings.AZURE_SEARCH_API_VERSION}"
        )
        search_headers = {
            "Content-Type": "application/json",
            "api-key": settings.AZURE_SEARCH_KEY,
        }

        total_succeeded = 0
        total_failed = 0
        total_batches = (len(employees) + args.batch_size - 1) // args.batch_size

        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as http_session:
            for batch_idx in range(total_batches):
                start = batch_idx * args.batch_size
                end = min(start + args.batch_size, len(employees))
                batch = employees[start:end]

                logger.info(
                    "Processing batch %d/%d (%d employees)...",
                    batch_idx + 1,
                    total_batches,
                    len(batch),
                )

                try:
                    texts = [build_searchable_text(doc) for doc in batch]

                    if args.dry_run:
                        embeddings: list[list[float]] = [[0.0] * settings.OPENAI_EMBEDDING_DIMENSIONS] * len(batch)
                    else:
                        assert openai_client is not None
                        resp = await openai_client.embeddings.create(
                            input=texts,
                            model=settings.OPENAI_EMBEDDING_MODEL,
                            dimensions=settings.OPENAI_EMBEDDING_DIMENSIONS,
                        )
                        embeddings = [item.embedding for item in resp.data]

                    documents = [build_search_document(doc, emb) for doc, emb in zip(batch, embeddings)]

                    succeeded, failed = await upload_batch(
                        http_session,
                        search_url,
                        search_headers,
                        documents,
                        dry_run=args.dry_run,
                    )
                    total_succeeded += succeeded
                    total_failed += failed

                    logger.info(
                        "Batch %d/%d: %d succeeded, %d failed",
                        batch_idx + 1,
                        total_batches,
                        succeeded,
                        failed,
                    )
                except Exception:
                    logger.exception(
                        "Batch %d/%d failed — continuing...",
                        batch_idx + 1,
                        total_batches,
                    )
                    total_failed += len(batch)

                if batch_idx < total_batches - 1:
                    await asyncio.sleep(1)
    finally:
        await cosmos_client.close()

    logger.info("=" * 50)
    logger.info("Re-indexing complete!")
    logger.info("Total succeeded: %d", total_succeeded)
    logger.info("Total failed: %d", total_failed)
    logger.info("Total employees: %d", len(employees))
    if args.dry_run:
        logger.info("[DRY RUN] No documents were actually uploaded.")


def main() -> None:
    args = parse_args()
    asyncio.run(reindex(args))


if __name__ == "__main__":
    main()
