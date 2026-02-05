from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.models.auth import UserInfo
from app.models.employee import EmployeeDetail, EmployeeSummary
from app.services.employee_service import employee_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeSummary])
async def list_employees(
    skip: int = 0,
    limit: int = 50,
    user: UserInfo = Depends(get_current_user),
):
    try:
        return await employee_service.get_employees(skip=skip, limit=limit)
    except Exception:
        logger.exception("Failed to list employees")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve employees",
        )


@router.get("/{alias}", response_model=EmployeeDetail)
async def get_employee(
    alias: str,
    user: UserInfo = Depends(get_current_user),
):
    try:
        employee = await employee_service.get_employee_by_alias(alias)
    except Exception:
        logger.exception("Failed to get employee %s", alias)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve employee",
        )

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with alias '{alias}' not found",
        )

    return employee
