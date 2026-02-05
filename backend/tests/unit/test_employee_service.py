from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.employee import EmployeeDetail, EmployeeSummary
from app.services.employee_service import EmployeeService, _calculate_experience


SAMPLE_COSMOS_DOC = {
    "id": "JDOE",
    "Alias": "JDOE",
    "Employee": "Doe, John",
    "First Name": "John",
    "Last Name": "Doe",
    "Job Title": "Senior Developer",
    "Employee ID": "E12345",
    "Job Code": "DEV-3",
    "Project Role": "Tech Lead",
    "Experience Level": "Senior",
    "Unit": "Engineering",
    "Manager": "Smith, Jane",
    "Manager Alias": "JSMI",
    "Company": "Emposo GmbH",
    "Phone": "+49 123 456789",
    "Email": "john.doe@emposo.de",
    "Office": "Berlin HQ",
    "Department": "IT",
    "Division": "Product",
    "Location": "Berlin",
    "Start": "2020-01-15",
}


def test_transform_employee_maps_fields():
    service = EmployeeService()
    result = service._transform_employee(SAMPLE_COSMOS_DOC)

    assert isinstance(result, EmployeeDetail)
    assert result.id == "JDOE"
    assert result.name == "Doe, John"
    assert result.first_name == "John"
    assert result.last_name == "Doe"
    assert result.title == "Senior Developer"
    assert result.employee_id == "E12345"
    assert result.job_code == "DEV-3"
    assert result.project_role == "Tech Lead"
    assert result.experience_level == "Senior"
    assert result.unit == "Engineering"
    assert result.manager == "Smith, Jane"
    assert result.manager_alias == "JSMI"
    assert result.company == "Emposo GmbH"
    assert result.phone == "+49 123 456789"
    assert result.email == "john.doe@emposo.de"
    assert result.office == "Berlin HQ"
    assert result.department == "IT"
    assert result.division == "Product"
    assert result.location == "Berlin"
    assert result.start_date == "2020-01-15"
    assert result.years_of_experience != "N/A"


def test_transform_employee_uses_new_job_title_fallback():
    doc = {"id": "TEST", "New Job Title": "Fallback Title"}
    service = EmployeeService()
    result = service._transform_employee(doc)

    assert result.title == "Fallback Title"


def test_transform_employee_handles_empty_doc():
    service = EmployeeService()
    result = service._transform_employee({})

    assert result.id == "unknown"
    assert result.name is None
    assert result.years_of_experience == "N/A"


def test_calculate_experience_with_valid_date():
    result = _calculate_experience("2020-01-01")
    assert result != "N/A"
    assert float(result) > 0


def test_calculate_experience_with_none():
    assert _calculate_experience(None) == "N/A"


def test_calculate_experience_with_invalid_date():
    assert _calculate_experience("not-a-date") == "N/A"


@pytest.mark.anyio
async def test_get_employee_by_alias_found():
    service = EmployeeService()
    service.initialized = True

    mock_container = MagicMock()

    async def mock_query_items(**kwargs):
        yield SAMPLE_COSMOS_DOC

    mock_container.query_items = mock_query_items
    service.container = mock_container

    result = await service.get_employee_by_alias("JDOE")

    assert result is not None
    assert isinstance(result, EmployeeDetail)
    assert result.id == "JDOE"
    assert result.name == "Doe, John"


@pytest.mark.anyio
async def test_get_employee_by_alias_not_found():
    service = EmployeeService()
    service.initialized = True

    mock_container = MagicMock()

    async def mock_query_items(**kwargs):
        return
        yield  # noqa: unreachable — makes this an async generator

    mock_container.query_items = mock_query_items
    service.container = mock_container

    result = await service.get_employee_by_alias("NONEXISTENT")
    assert result is None


@pytest.mark.anyio
async def test_get_employee_by_alias_not_initialized():
    service = EmployeeService()
    result = await service.get_employee_by_alias("JDOE")
    assert result is None


@pytest.mark.anyio
async def test_get_employees_returns_list():
    service = EmployeeService()
    service.initialized = True

    mock_container = MagicMock()

    async def mock_query_items(**kwargs):
        yield SAMPLE_COSMOS_DOC

    mock_container.query_items = mock_query_items
    service.container = mock_container

    results = await service.get_employees(skip=0, limit=10)

    assert len(results) == 1
    assert isinstance(results[0], EmployeeSummary)
    assert results[0].id == "JDOE"
    assert results[0].name == "Doe, John"
    assert results[0].email == "john.doe@emposo.de"


@pytest.mark.anyio
async def test_get_employees_not_initialized():
    service = EmployeeService()
    results = await service.get_employees()
    assert results == []


@pytest.mark.anyio
async def test_check_connection_success():
    service = EmployeeService()
    service.initialized = True

    mock_container = MagicMock()

    async def mock_query_items(**kwargs):
        yield 42

    mock_container.query_items = mock_query_items
    service.container = mock_container

    assert await service.check_connection() is True


@pytest.mark.anyio
async def test_check_connection_not_initialized():
    service = EmployeeService()
    assert await service.check_connection() is False
