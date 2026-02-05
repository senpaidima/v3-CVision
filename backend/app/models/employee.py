"""Employee models for Cosmos DB employee data."""

from __future__ import annotations

from pydantic import BaseModel


class EmployeeSummary(BaseModel):
    """Minimal employee info for lists and search results."""

    id: str
    name: str | None = None
    title: str | None = None
    department: str | None = None
    unit: str | None = None
    location: str | None = None
    email: str | None = None


class EmployeeDetail(EmployeeSummary):
    """Full employee details from Cosmos DB."""

    first_name: str | None = None
    last_name: str | None = None
    employee_id: str | None = None
    job_code: str | None = None
    project_role: str | None = None
    experience_level: str | None = None
    manager: str | None = None
    manager_alias: str | None = None
    company: str | None = None
    phone: str | None = None
    office: str | None = None
    division: str | None = None
    start_date: str | None = None
    years_of_experience: str = "N/A"
