from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.auth import UserInfo
from app.services.employee_service import employee_service

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    services: dict[str, str] = {}

    try:
        if employee_service.initialized:
            ok = await employee_service.check_connection()
            services["cosmos_db"] = "ok" if ok else "error"
        else:
            services["cosmos_db"] = "not_configured"
    except Exception:
        services["cosmos_db"] = "error"

    services["azure_search"] = "not_configured"
    services["azure_openai"] = "not_configured"

    all_ok = all(v in ("ok", "not_configured") for v in services.values())

    return {
        "status": "healthy" if all_ok else "degraded",
        "version": settings.APP_VERSION,
        "services": services,
    }


@router.get("/protected")
async def health_protected(user: UserInfo = Depends(get_current_user)):
    return {"status": "ok", "user": user.model_dump()}


@router.get("/ready")
async def readiness_probe():
    return {"ready": True}
