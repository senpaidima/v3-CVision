from __future__ import annotations


def test_health_returns_status_and_services(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "version" in data
    assert "services" in data
    assert "cosmos_db" in data["services"]
    assert "azure_search" in data["services"]
    assert "azure_openai" in data["services"]


def test_health_not_configured_is_healthy(client):
    response = client.get("/api/v1/health")
    data = response.json()
    assert data["status"] == "healthy"
    assert data["services"]["cosmos_db"] == "not_configured"
    assert data["services"]["azure_search"] == "not_configured"
    assert data["services"]["azure_openai"] == "not_configured"


def test_readiness_probe(client):
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True


def test_health_protected_requires_auth(client):
    response = client.get("/api/v1/health/protected")
    assert response.status_code == 401


def test_health_protected_with_auth(authenticated_client):
    response = authenticated_client.get("/api/v1/health/protected")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "user" in data
