def test_root_returns_message(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "CVision v3 API"


def test_health_returns_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert data["version"] == "0.1.0"
