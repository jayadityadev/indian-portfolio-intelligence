from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "version" in body


def test_http_errors_use_api_envelope() -> None:
    response = client.get("/api/v1/market/UNKNOWN.NS/series")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"
    assert response.json()["ok"] is False


def test_validation_errors_use_api_envelope() -> None:
    response = client.post("/api/v1/backtest", json={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
