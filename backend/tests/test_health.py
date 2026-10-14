"""Unit and API tests for health and readiness endpoints."""

from unittest.mock import patch

from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "ProofLens AI"
    assert data["status"] == "online"
    assert "version" in data


def test_health_liveness(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}


def test_readiness_success(client: TestClient):
    with patch("prooflens.api.v1.routes.health.check_database_readiness") as mock_check:
        mock_check.return_value = {"database": "ok", "vector_extension": "ok"}
        response = client.get("/api/v1/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["checks"]["database"] == "ok"
        assert data["checks"]["vector_extension"] == "ok"


def test_readiness_failure(client: TestClient):
    with patch("prooflens.api.v1.routes.health.check_database_readiness") as mock_check:
        mock_check.side_effect = Exception("Database connection refused")
        response = client.get("/api/v1/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["database"] == "error"


def test_request_headers_and_middleware(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time-Ms" in response.headers


def test_error_envelope_on_404(client: TestClient):
    response = client.get("/api/v1/non_existent_route")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "request_id" in data["error"]
