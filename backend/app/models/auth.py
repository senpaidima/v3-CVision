"""Authentication models for Azure AD JWT tokens."""

from __future__ import annotations

from pydantic import BaseModel


class TokenPayload(BaseModel):
    oid: str | None = None
    name: str | None = None
    preferred_username: str | None = None
    roles: list[str] = []


class UserInfo(BaseModel):
    id: str | None = None
    name: str | None = None
    email: str | None = None
    roles: list[str] = []
