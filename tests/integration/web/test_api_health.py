"""Integration tests for GET /api/health."""

import pytest


@pytest.mark.integration
class TestHealth:
    def test_health_reports_db_redis_processor(self, client, lamp):
        resp = client.get("/api/health")
        body = resp.get_json()
        assert set(body["services"]) == {"database", "redis", "processor"}
        assert body["services"]["database"]["status"] == "healthy"
        assert body["services"]["redis"]["status"] == "healthy"
        assert "latency_ms" in body["services"]["redis"]
        # No processor_heartbeat table in the test DB: reported, not fatal.
        assert body["services"]["processor"]["status"] in ("error", "unknown")
        assert body["metrics"]["total_arduinos"] == 1
        assert resp.status_code == 200

    def test_health_unhealthy_when_redis_client_missing(self, client, lamp):
        import redis_manager
        redis_manager.redis_client = None  # REDIS_URL unset -> no client
        resp = client.get("/api/health")
        body = resp.get_json()
        assert body["services"]["redis"]["status"] == "down"
        assert body["status"] == "unhealthy"
        assert resp.status_code == 503

    def test_health_degraded_when_redis_errors(self, client, lamp):
        import redis_manager

        class Raising:
            def ping(self):
                raise ConnectionError("nope")

        redis_manager.redis_client = Raising()
        body = client.get("/api/health").get_json()
        assert body["services"]["redis"]["status"] == "down"
        assert body["services"]["redis"]["error"] == "nope"

    def test_health_has_timestamp(self, client):
        body = client.get("/api/health").get_json()
        assert body["timestamp"].endswith("+00:00")
