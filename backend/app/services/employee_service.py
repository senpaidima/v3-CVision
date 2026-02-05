"""Cosmos DB employee service (read-only)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from azure.cosmos.aio import CosmosClient

from app.core.config import Settings
from app.models.employee import EmployeeDetail, EmployeeSummary

logger = logging.getLogger(__name__)

# Cosmos DB field names (with spaces) → Python snake_case attribute names
_FIELD_MAP: list[tuple[str, str]] = [
    ("name", "Employee"),
    ("first_name", "First Name"),
    ("last_name", "Last Name"),
    ("title", "Job Title"),
    ("employee_id", "Employee ID"),
    ("job_code", "Job Code"),
    ("project_role", "Project Role"),
    ("experience_level", "Experience Level"),
    ("unit", "Unit"),
    ("manager", "Manager"),
    ("manager_alias", "Manager Alias"),
    ("company", "Company"),
    ("phone", "Phone"),
    ("email", "Email"),
    ("office", "Office"),
    ("department", "Department"),
    ("division", "Division"),
    ("location", "Location"),
    ("start_date", "Start"),
]


def _calculate_experience(start_date: str | None) -> str:
    if not start_date:
        return "N/A"
    try:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d.%m.%Y"):
            try:
                start = datetime.strptime(start_date, fmt)  # noqa: DTZ007
                years = (datetime.now() - start).days / 365.25  # noqa: DTZ005
                return f"{years:.1f}"
            except ValueError:
                continue
        return "N/A"
    except Exception:
        return "N/A"


class EmployeeService:
    def __init__(self) -> None:
        self.client: CosmosClient | None = None
        self.container: Any = None
        self.initialized: bool = False

    async def initialize(self, settings: Settings) -> None:
        if self.initialized:
            return

        endpoint = settings.COSMOS_DB_ENDPOINT
        key = settings.COSMOS_DB_KEY
        database_name = settings.COSMOS_DB_DATABASE
        container_name = settings.COSMOS_DB_EMPLOYEES_CONTAINER

        if not endpoint or not key:
            logger.warning("Cosmos DB credentials missing — service not initialized")
            return

        self.client = CosmosClient(endpoint, key)
        db = self.client.get_database_client(database_name)
        self.container = db.get_container_client(container_name)
        self.initialized = True
        logger.info("EmployeeService initialized (container=%s)", container_name)

    async def close(self) -> None:
        if self.client:
            await self.client.close()
            self.client = None
            self.container = None
            self.initialized = False

    async def get_employee_by_alias(self, alias: str) -> EmployeeDetail | None:
        if not self.container:
            return None

        query = 'SELECT * FROM c WHERE c.id = @alias OR c.Alias = @alias OR c["Employee ID"] = @alias'
        params: list[dict[str, str]] = [{"name": "@alias", "value": alias}]

        items: list[dict[str, Any]] = []
        async for item in self.container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True,
        ):
            items.append(item)

        if not items:
            return None

        return self._transform_employee(items[0])

    async def get_employees(self, skip: int = 0, limit: int = 50) -> list[EmployeeSummary]:
        if not self.container:
            return []

        query = "SELECT * FROM c OFFSET @skip LIMIT @limit"
        params: list[dict[str, Any]] = [
            {"name": "@skip", "value": skip},
            {"name": "@limit", "value": limit},
        ]

        results: list[EmployeeSummary] = []
        async for item in self.container.query_items(
            query=query,
            parameters=params,
            enable_cross_partition_query=True,
        ):
            detail = self._transform_employee(item)
            results.append(
                EmployeeSummary(
                    id=detail.id,
                    name=detail.name,
                    title=detail.title,
                    department=detail.department,
                    unit=detail.unit,
                    location=detail.location,
                    email=detail.email,
                )
            )

        return results

    async def check_connection(self) -> bool:
        if not self.container:
            return False
        try:
            query = "SELECT VALUE COUNT(1) FROM c"
            async for _ in self.container.query_items(
                query=query,
                enable_cross_partition_query=True,
            ):
                return True
            return True
        except Exception:
            logger.exception("Cosmos DB connection check failed")
            return False

    def _transform_employee(self, raw: dict[str, Any]) -> EmployeeDetail:
        data: dict[str, Any] = {
            "id": raw.get("id") or raw.get("Alias") or "unknown",
            "years_of_experience": "N/A",
        }

        for python_key, cosmos_key in _FIELD_MAP:
            data[python_key] = raw.get(cosmos_key)

        # Fallback: "New Job Title" if "Job Title" is empty
        if not data.get("title"):
            data["title"] = raw.get("New Job Title")

        data["years_of_experience"] = _calculate_experience(data.get("start_date"))

        return EmployeeDetail(**data)


employee_service = EmployeeService()
