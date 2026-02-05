from __future__ import annotations

import logging

from fastapi import Depends, Header, HTTPException, status

from app.core.auth import extract_roles_from_token, validate_token
from app.core.config import settings
from app.models.auth import UserInfo

logger = logging.getLogger(__name__)


async def get_current_user(authorization: str | None = Header(None)) -> UserInfo:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ", 1)[1]

    try:
        payload = validate_token(
            token,
            settings.AZURE_AD_TENANT_ID,
            settings.AZURE_AD_CLIENT_ID,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token validation error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    roles = extract_roles_from_token(payload)
    return UserInfo(
        id=payload.get("oid"),
        name=payload.get("name"),
        email=payload.get("preferred_username"),
        roles=roles,
    )


def require_role(*roles: str):
    async def _check_role(user: UserInfo = Depends(get_current_user)) -> UserInfo:
        if not any(r in user.roles for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {', '.join(roles)}",
            )
        return user

    return _check_role
