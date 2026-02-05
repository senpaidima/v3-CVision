from __future__ import annotations

import base64
import time

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from httpx import ASGITransport, AsyncClient
from jose import jwt
from starlette.testclient import TestClient

from app.core.dependencies import get_current_user
from app.main import app
from app.models.auth import UserInfo

TEST_TENANT_ID = "test-tenant-00000000-0000-0000-0000-000000000000"
TEST_CLIENT_ID = "test-client-00000000-0000-0000-0000-000000000000"
TEST_KID = "test-kid-1"


def _int_to_base64url(value: int) -> str:
    byte_length = (value.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(value.to_bytes(byte_length, byteorder="big")).rstrip(b"=").decode("ascii")


@pytest.fixture(autouse=True)
def _auth_settings():
    from app.core.config import settings

    original_tenant = settings.AZURE_AD_TENANT_ID
    original_client = settings.AZURE_AD_CLIENT_ID
    settings.AZURE_AD_TENANT_ID = TEST_TENANT_ID
    settings.AZURE_AD_CLIENT_ID = TEST_CLIENT_ID
    yield
    settings.AZURE_AD_TENANT_ID = original_tenant
    settings.AZURE_AD_CLIENT_ID = original_client


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def rsa_test_keys():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("utf-8")

    pub = private_key.public_key().public_numbers()
    jwk_dict = {
        "kty": "RSA",
        "kid": TEST_KID,
        "use": "sig",
        "alg": "RS256",
        "n": _int_to_base64url(pub.n),
        "e": _int_to_base64url(pub.e),
    }
    jwks_response = {"keys": [jwk_dict]}
    return private_pem, jwks_response


def _make_token(
    private_pem: str,
    *,
    oid: str = "test-oid-123",
    name: str = "Test User",
    email: str = "test@emposo.de",
    roles: list[str] | None = None,
    expired: bool = False,
) -> str:
    now = int(time.time())
    claims = {
        "oid": oid,
        "name": name,
        "preferred_username": email,
        "roles": roles or [],
        "iss": f"https://login.microsoftonline.com/{TEST_TENANT_ID}/v2.0",
        "aud": TEST_CLIENT_ID,
        "exp": now - 3600 if expired else now + 3600,
        "iat": now - 60,
        "nbf": now - 60,
    }
    return jwt.encode(claims, private_pem, algorithm="RS256", headers={"kid": TEST_KID})


@pytest.fixture
def mock_user_viewer():
    return UserInfo(id="viewer-1", name="Viewer User", email="viewer@emposo.de", roles=["viewer"])


@pytest.fixture
def mock_user_admin():
    return UserInfo(id="admin-1", name="Admin User", email="admin@emposo.de", roles=["admin"])


@pytest.fixture
def mock_user_sales():
    return UserInfo(id="sales-1", name="Sales User", email="sales@emposo.de", roles=["sales"])


@pytest.fixture
def authenticated_client(mock_user_admin):
    app.dependency_overrides[get_current_user] = lambda: mock_user_admin
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
