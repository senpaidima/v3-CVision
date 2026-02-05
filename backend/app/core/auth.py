"""Azure AD JWT authentication — token validation and JWKS caching."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

from fastapi import HTTPException, status
from jose import jwk, jwt
from jose.constants import Algorithms
from jose.exceptions import ExpiredSignatureError, JWSSignatureError, JWTClaimsError, JWTError

logger = logging.getLogger("azure_auth")

_JWKS_TTL_SECONDS = 24 * 60 * 60

_cache: dict[str, Any] = {
    "jwks": {},
    "jwks_timestamp": {},
}


def get_jwks(tenant_id: str) -> dict[str, Any]:
    cache_key = f"jwks_{tenant_id}"
    now = time.time()

    if (
        cache_key in _cache["jwks"]
        and cache_key in _cache["jwks_timestamp"]
        and now - _cache["jwks_timestamp"][cache_key] < _JWKS_TTL_SECONDS
    ):
        return _cache["jwks"][cache_key]

    jwks_uri = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
    logger.info("Fetching JWKS from %s", jwks_uri)

    try:
        req = urllib.request.Request(jwks_uri)  # noqa: S310
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            jwks = json.loads(resp.read().decode())

        _cache["jwks"][cache_key] = jwks
        _cache["jwks_timestamp"][cache_key] = now
        return jwks
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        logger.error("Failed to fetch JWKS: %s", e)
        if cache_key in _cache["jwks"]:
            logger.warning("Using expired JWKS from cache for tenant %s", tenant_id)
            return _cache["jwks"][cache_key]
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not fetch JWKS: {e}",
        ) from e


def get_signing_key(token: str, tenant_id: str) -> dict[str, str]:
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token header: {e}",
        ) from e

    kid = header.get("kid")
    if not kid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has no 'kid' in header",
        )

    jwks = get_jwks(tenant_id)
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"No matching signing key for kid: {kid}",
    )


def validate_token(token: str, tenant_id: str, client_id: str) -> dict[str, Any]:
    if not tenant_id or not client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing Azure AD configuration",
        )

    signing_key_dict = get_signing_key(token, tenant_id)
    algorithm = signing_key_dict.get("alg", Algorithms.RS256)
    public_key = jwk.construct(signing_key_dict, algorithm=algorithm)

    expected_issuers = [
        f"https://login.microsoftonline.com/{tenant_id}/v2.0",
        f"https://sts.windows.net/{tenant_id}/",
    ]
    expected_audiences = [client_id, f"api://{client_id}"]

    options = {
        "verify_signature": True,
        "verify_aud": True,
        "verify_iss": True,
        "verify_exp": True,
        "require": ["exp", "iss", "aud"],
    }

    last_error: Exception | None = None

    for issuer in expected_issuers:
        for audience in expected_audiences:
            try:
                return jwt.decode(
                    token,
                    public_key,
                    algorithms=[algorithm],
                    audience=audience,
                    issuer=issuer,
                    options=options,
                )
            except ExpiredSignatureError as e:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token is expired",
                ) from e
            except JWSSignatureError as e:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token signature",
                ) from e
            except (JWTClaimsError, JWTError) as e:
                last_error = e
                continue

    detail = "Invalid authentication credentials"
    if isinstance(last_error, JWTClaimsError) and "audience" in str(last_error).lower():
        detail = f"Invalid token audience. Expected one of: {expected_audiences}"
    elif isinstance(last_error, JWTClaimsError) and "issuer" in str(last_error).lower():
        detail = f"Invalid token issuer. Expected one of: {expected_issuers}"

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
    )


def extract_roles_from_token(payload: dict[str, Any]) -> list[str]:
    roles = payload.get("roles", [])
    if not isinstance(roles, list):
        return []
    return [str(r) for r in roles if isinstance(r, str | int)]
