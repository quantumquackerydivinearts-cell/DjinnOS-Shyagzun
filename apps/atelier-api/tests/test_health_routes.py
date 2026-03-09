from __future__ import annotations

from fastapi.testclient import TestClient

from atelier_api.main import _atelier_service, app


class _HealthyService:
    def health(self) -> None:
        return None


class _DegradedService:
    def health(self) -> None:
        raise RuntimeError("database_unreachable")


def test_health_returns_ok_when_service_is_healthy() -> None:
    app.dependency_overrides[_atelier_service] = lambda: _HealthyService()
    try:
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "api": "up", "database": "up"}
    finally:
        app.dependency_overrides.pop(_atelier_service, None)


def test_health_returns_degraded_when_service_health_check_fails() -> None:
    app.dependency_overrides[_atelier_service] = lambda: _DegradedService()
    try:
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "degraded"
        assert payload["api"] == "up"
        assert payload["database"] == "down"
        assert "database_unreachable" in payload["detail"]
    finally:
        app.dependency_overrides.pop(_atelier_service, None)


def test_ready_returns_503_when_service_health_check_fails() -> None:
    app.dependency_overrides[_atelier_service] = lambda: _DegradedService()
    try:
        client = TestClient(app)
        response = client.get("/ready")
        assert response.status_code == 503
        payload = response.json()["detail"]
        assert payload["status"] == "not_ready"
        assert payload["api"] == "up"
        assert payload["database"] == "down"
        assert "database_unreachable" in payload["detail"]
    finally:
        app.dependency_overrides.pop(_atelier_service, None)
