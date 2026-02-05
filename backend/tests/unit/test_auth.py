from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.core.auth import extract_roles_from_token, validate_token
from app.core.dependencies import require_role
from tests.conftest import TEST_CLIENT_ID, TEST_TENANT_ID, _make_token


def test_missing_auth_header_returns_401(client):
    response = client.get("/api/v1/health/protected")
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


def test_invalid_token_returns_401(client):
    response = client.get(
        "/api/v1/health/protected",
        headers={"Authorization": "Bearer not-a-valid-jwt-token"},
    )
    assert response.status_code == 401


@patch("app.core.auth.get_jwks")
def test_expired_token_returns_401(mock_get_jwks, client, rsa_test_keys):
    private_pem, jwks_response = rsa_test_keys
    mock_get_jwks.return_value = jwks_response

    expired_token = _make_token(private_pem, expired=True)

    response = client.get(
        "/api/v1/health/protected",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_valid_token_returns_user(authenticated_client):
    response = authenticated_client.get("/api/v1/health/protected")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["user"]["id"] == "admin-1"
    assert data["user"]["name"] == "Admin User"
    assert data["user"]["email"] == "admin@emposo.de"
    assert "admin" in data["user"]["roles"]


@pytest.mark.anyio
async def test_role_check_passes_with_correct_role(mock_user_admin):
    checker = require_role("admin")
    result = await checker(user=mock_user_admin)
    assert result.id == "admin-1"
    assert "admin" in result.roles


@pytest.mark.anyio
async def test_role_check_fails_with_wrong_role(mock_user_viewer):
    checker = require_role("admin")
    with pytest.raises(HTTPException) as exc_info:
        await checker(user=mock_user_viewer)
    assert exc_info.value.status_code == 403
    assert "Insufficient permissions" in exc_info.value.detail


def test_extract_roles_from_token_with_roles():
    payload = {"roles": ["admin", "viewer"]}
    assert extract_roles_from_token(payload) == ["admin", "viewer"]


def test_extract_roles_from_token_empty():
    assert extract_roles_from_token({}) == []


def test_extract_roles_from_token_invalid_type():
    assert extract_roles_from_token({"roles": "not-a-list"}) == []


@patch("app.core.auth.get_jwks")
def test_validate_token_with_valid_token(mock_get_jwks, rsa_test_keys):
    private_pem, jwks_response = rsa_test_keys
    mock_get_jwks.return_value = jwks_response

    token = _make_token(private_pem, roles=["admin", "viewer"])
    payload = validate_token(token, TEST_TENANT_ID, TEST_CLIENT_ID)

    assert payload["oid"] == "test-oid-123"
    assert payload["name"] == "Test User"
    assert payload["roles"] == ["admin", "viewer"]


def test_validate_token_missing_config():
    with pytest.raises(HTTPException) as exc_info:
        validate_token("any-token", "", "")
    assert exc_info.value.status_code == 500
