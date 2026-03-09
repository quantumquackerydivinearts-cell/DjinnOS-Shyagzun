from __future__ import annotations

from fastapi.testclient import TestClient

from atelier_api.main import _atelier_service, app


class _HealthyService:
    def health(self) -> None:
        return None

    def get_readiness_status(self) -> dict[str, object]:
        return {
            "status": "ready",
            "api": {"status": "up"},
            "database": {"status": "up"},
            "kernel": {"status": "up"},
            "migrations": {"status": "up", "up_to_date": True},
            "config": {"status": "up", "issues": []},
        }

    def get_federation_health(self, *, distribution_id=None, limit=25) -> dict[str, object]:
        return {
            "status": "ok",
            "local_protocol": {"family": "guild_message_signal_artifice", "version": "v1", "supported_versions": ["v1"]},
            "readiness": self.get_readiness_status(),
            "target_count": 1,
            "active_trust_count": 1,
            "error_count": 0,
            "targets": [
                {
                    "distribution_id": distribution_id or "distribution.remote",
                    "status": "reachable",
                    "trust_grade": "active",
                }
            ],
        }


class _DegradedService:
    def health(self) -> None:
        raise RuntimeError("database_unreachable")

    def get_readiness_status(self) -> dict[str, object]:
        return {
            "status": "not_ready",
            "api": {"status": "up"},
            "database": {"status": "down", "detail": "database_unreachable"},
            "kernel": {"status": "down", "detail": "kernel_unreachable"},
            "migrations": {"status": "down", "detail": "migration_pending"},
            "config": {"status": "warning", "issues": ["database_url_local_default"]},
        }

    def get_federation_health(self, *, distribution_id=None, limit=25) -> dict[str, object]:
        return {
            "status": "degraded",
            "local_protocol": {"family": "guild_message_signal_artifice", "version": "v1", "supported_versions": ["v1"]},
            "readiness": self.get_readiness_status(),
            "target_count": 1,
            "active_trust_count": 0,
            "error_count": 1,
            "targets": [
                {
                    "distribution_id": distribution_id or "distribution.remote",
                    "status": "error",
                    "trust_grade": "unreachable",
                }
            ],
        }


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
        payload = response.json()
        assert payload["status"] == "not_ready"
        assert payload["api"]["status"] == "up"
        assert payload["database"]["status"] == "down"
        assert "database_unreachable" in payload["database"]["detail"]
    finally:
        app.dependency_overrides.pop(_atelier_service, None)


def test_federation_health_returns_aggregate_summary() -> None:
    app.dependency_overrides[_atelier_service] = lambda: _HealthyService()
    try:
        client = TestClient(app)
        response = client.get("/v1/federation/health?distribution_id=distribution.remote")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["target_count"] == 1
        assert payload["targets"][0]["distribution_id"] == "distribution.remote"
        assert payload["targets"][0]["trust_grade"] == "active"
    finally:
        app.dependency_overrides.pop(_atelier_service, None)
