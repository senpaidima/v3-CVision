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
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d.%m.%Y", "%Y-%m", "%Y"):
        try:
            start = datetime.strptime(start_date, fmt)  # noqa: DTZ007
            years = (datetime.now() - start).days / 365.25  # noqa: DTZ005
            return round(years, 1)
        except ValueError:
            continue
    return 0.0


def _get_all_skills(doc: dict[str, Any]) -> list[str]:
    """Extract all skills from nested skills object."""
    skills_obj = doc.get("skills", {})
    if not isinstance(skills_obj, dict):
        return []
    all_skills: list[str] = []
    for key in ("tools", "technologies", "methods", "standards", "soft_skills"):
        items = skills_obj.get(key, [])
        if isinstance(items, list):
            all_skills.extend(str(s) for s in items if s)
    return all_skills


def _get_tools(doc: dict[str, Any]) -> list[str]:
    """Extract tools from nested skills object."""
    skills_obj = doc.get("skills", {})
    if not isinstance(skills_obj, dict):
        return []
    tools = skills_obj.get("tools", [])
    return [str(t) for t in tools if t] if isinstance(tools, list) else []


def _get_experience_text(doc: dict[str, Any]) -> str:
    """Build experience summary from experience array."""
    experiences = doc.get("experience", [])
    if not isinstance(experiences, list):
        return ""
    parts: list[str] = []
    for exp in experiences:
        if not isinstance(exp, dict):
            continue
        title = exp.get("title", "")
        company = exp.get("company", "")
        role = exp.get("role", "")
        desc = exp.get("description", "")
        tasks = exp.get("tasks", [])
        areas = exp.get("areas_of_expertise", [])
        line_parts = [p for p in [title, company, role] if p]
        if tasks and isinstance(tasks, list):
            line_parts.append(f"Tasks: {', '.join(str(t) for t in tasks)}")
        if areas and isinstance(areas, list):
            line_parts.append(f"Expertise: {', '.join(str(a) for a in areas)}")
        if desc:
            line_parts.append(desc)
        if line_parts:
            parts.append(" | ".join(line_parts))
    return "; ".join(parts)


def _get_projects_text(doc: dict[str, Any]) -> str:
    """Extract project titles from experience array."""
    experiences = doc.get("experience", [])
    if not isinstance(experiences, list):
        return ""
    projects = []
    for exp in experiences:
        if isinstance(exp, dict) and exp.get("type") == "project":
            title = exp.get("title", "")
            if title:
                projects.append(title)
    return ", ".join(projects)


def _get_latest_title(doc: dict[str, Any]) -> str:
    """Get the latest job title from experience."""
    experiences = doc.get("experience", [])
    if not isinstance(experiences, list):
        return ""
    for exp in experiences:
        if isinstance(exp, dict) and exp.get("type") == "job":
            title = exp.get("title", "")
            if title:
                return title
    # Fallback to any experience title
    for exp in experiences:
        if isinstance(exp, dict):
            title = exp.get("title", "")
            if title:
                return title
    return ""


def _get_earliest_start(doc: dict[str, Any]) -> str | None:
    """Find the earliest start date from experience."""
    experiences = doc.get("experience", [])
    if not isinstance(experiences, list):
        return None
    dates: list[str] = []
    for exp in experiences:
        if isinstance(exp, dict):
            sd = exp.get("start_date", "")
            if sd:
                dates.append(sd)
    return min(dates) if dates else None


def build_searchable_text(doc: dict[str, Any]) -> str:
    """Build searchable text from a Cosmos DB employee document.

    Cosmos DB documents have nested structure with metadata, skills, experience, etc.
    This function concatenates key fields into a single string for embedding.
    """
    parts: list[str] = []

    # Name from metadata
    metadata = doc.get("metadata", {})
    name = ""
    if isinstance(metadata, dict):
        name = metadata.get("title", "")
        if not name:
            first = metadata.get("first_name", "")
            last = metadata.get("last_name", "")
            name = f"{first} {last}".strip()
    if name:
        parts.append(f"Name: {name}")

    # Latest job title
    title = _get_latest_title(doc)
    if title:
        parts.append(f"Title: {title}")

    # All skills (tools + technologies + methods + standards)
    all_skills = _get_all_skills(doc)
    if all_skills:
        parts.append(f"Skills: {', '.join(all_skills)}")

    # Tools specifically
    tools = _get_tools(doc)
    if tools:
        parts.append(f"Tools: {', '.join(tools)}")

    # Experience
    exp_text = _get_experience_text(doc)
    if exp_text:
        parts.append(f"Experience: {exp_text}")

    # Projects
    projects = _get_projects_text(doc)
    if projects:
        parts.append(f"Projects: {projects}")

    # Location
    personal = doc.get("personal_info", {})
    location = personal.get("location", "") if isinstance(personal, dict) else ""
    if location:
        parts.append(f"Location: {location}")

    # Education
    education = doc.get("education", [])
    if isinstance(education, list) and education:
        edu_parts = []
        for edu in education:
            if isinstance(edu, dict):
                degree = edu.get("degree", "")
                field = edu.get("field_of_study", "")
                inst = edu.get("institution", "")
                edu_parts.append(" - ".join(p for p in [degree, field, inst] if p))
        if edu_parts:
            parts.append(f"Education: {'; '.join(edu_parts)}")

    # Certifications
    certs = doc.get("certifications", [])
    if isinstance(certs, list) and certs:
        cert_titles = [c.get("title", "") for c in certs if isinstance(c, dict) and c.get("title")]
        if cert_titles:
            parts.append(f"Certifications: {', '.join(cert_titles)}")

    # Languages
    langs = doc.get("languages", [])
    if isinstance(langs, list) and langs:
        lang_parts = [
            f"{l.get('language', '')} ({l.get('proficiency', '')})"
            for l in langs
            if isinstance(l, dict) and l.get("language")
        ]
        if lang_parts:
            parts.append(f"Languages: {', '.join(lang_parts)}")

    # Industry knowledge
    industry = doc.get("industry_knowledge", {})
    if isinstance(industry, dict):
        industries = industry.get("industries", [])
        companies = industry.get("companies", [])
        if isinstance(industries, list) and industries:
            parts.append(f"Industries: {', '.join(str(i) for i in industries)}")
        if isinstance(companies, list) and companies:
            parts.append(f"Companies: {', '.join(str(c) for c in companies)}")

    return "\n".join(parts)


def build_search_document(doc: dict[str, Any], embedding: list[float]) -> dict[str, Any]:
    """Map Cosmos DB employee doc to search index fields."""
    doc_id = doc.get("id") or "unknown"
    metadata = doc.get("metadata", {})
    name = ""
    if isinstance(metadata, dict):
        name = metadata.get("title", "")
        if not name:
            first = metadata.get("first_name", "")
            last = metadata.get("last_name", "")
            name = f"{first} {last}".strip()

    all_skills = _get_all_skills(doc)
    tools = _get_tools(doc)
    personal = doc.get("personal_info", {})
    location = personal.get("location", "") if isinstance(personal, dict) else ""

    return {
        "@search.action": "mergeOrUpload",
        "id": str(doc_id),
        "employeeName": name,
        "employeeAlias": str(doc_id),
        "content": build_searchable_text(doc),
        "skills": all_skills,
        "tools": tools,
        "experience": _get_experience_text(doc),
        "projects": _get_projects_text(doc),
        "title": _get_latest_title(doc),
        "location": location,
        "department": "",
        "yearsOfExperience": _calculate_years(_get_earliest_start(doc)),
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
