"""
Integration tests for the older device endpoints still served for lamps
that have not been reflashed: V1 and V2 JSON, the heartbeat callback,
the fleet status overview, and server discovery.
"""

from datetime import datetime, timezone

import pytest
from freezegun import freeze_time

from ..conftest import LAMP_UA


@pytest.mark.integration
class TestV2:
    def test_v2_json_has_coordinates_and_tz(self, client, lamp):
        resp = client.get("/api/arduino/v2/14/data", headers=LAMP_UA)
        assert resp.status_code == 200
        body = resp.get_json()
        for key in ("latitude", "longitude", "tz_offset", "wave_height_cm", "wind_speed_mps",
                    "wave_threshold_cm", "wind_speed_threshold_knots", "fetch_interval_ms",
                    "quiet_hours_active", "off_hours_active", "brightness_multiplier"):
            assert key in body, key
        assert body["wave_height_cm"] == 120
        assert "sunset_animation" not in body  # V2 lamps computed sunset locally

    def test_v2_unknown_404(self, client, lamp):
        assert client.get("/api/arduino/v2/999/data", headers=LAMP_UA).status_code == 404

    def test_v2_records_heartbeat_for_lamp_ua(self, client, lamp, fake_redis):
        client.get("/api/arduino/v2/14/data", headers=LAMP_UA)
        assert fake_redis.hget("arduino:last_seen", "14") is not None


@pytest.mark.integration
class TestV1:
    def test_v1_json_has_sunset_fields(self, client, lamp):
        resp = client.get("/api/arduino/14/data", headers=LAMP_UA)
        assert resp.status_code == 200
        body = resp.get_json()
        assert "sunset_animation" in body
        assert "day_of_year" in body
        assert body["wave_height_cm"] == 120
        assert body["led_theme"] == "classic_surf"

    def test_v1_unknown_404(self, client, lamp):
        assert client.get("/api/arduino/999/data", headers=LAMP_UA).status_code == 404


@pytest.mark.integration
class TestCallback:
    def test_callback_updates_heartbeat(self, client, lamp, fake_redis):
        resp = client.post("/api/arduino/callback", json={"arduino_id": 14, "data_received": True}, headers=LAMP_UA)
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True
        assert fake_redis.hget("arduino:last_seen", "14") is not None

    def test_callback_missing_id_400(self, client, lamp):
        resp = client.post("/api/arduino/callback", json={"data_received": True}, headers=LAMP_UA)
        assert resp.status_code == 400

    def test_callback_no_json_400(self, client, lamp):
        resp = client.post("/api/arduino/callback", data="not json", content_type="text/plain", headers=LAMP_UA)
        assert resp.status_code == 400

    def test_callback_unknown_id_404(self, client, lamp):
        resp = client.post("/api/arduino/callback", json={"arduino_id": 999}, headers=LAMP_UA)
        assert resp.status_code == 404

    def test_callback_redis_down_uses_throttled_db_fallback(self, client, lamp, db_session, monkeypatch):
        """With Redis unavailable the callback must still succeed and write
        last_poll_time. Guards three past bugs on this path: the
        UnboundLocalError in record_db_write, the DetachedInstanceError from
        reading the arduino after its session closed, and `None += 1` on the
        first redis_health failure row. Sampling is forced to pass."""
        import redis_manager
        from data_base import Arduino, RedisHealth

        redis_manager.redis_client = None                              # REDIS_URL unset -> no client
        monkeypatch.setattr(redis_manager.random, "random", lambda: 0.0)  # sampling gate always passes
        old = db_session.query(Arduino).filter_by(arduino_id=14).one().last_poll_time

        resp = client.post("/api/arduino/callback", json={"arduino_id": 14}, headers=LAMP_UA)

        assert resp.status_code == 200, resp.get_json()
        db_session.expire_all()
        assert db_session.query(Arduino).filter_by(arduino_id=14).one().last_poll_time >= old
        health = db_session.query(RedisHealth).filter_by(service_name="web-service").one()
        assert health.consecutive_failures == 1
        assert health.is_healthy is True   # unhealthy only after 3 consecutive failures

    def test_callback_redis_down_rate_limited_write_still_200(self, client, lamp, monkeypatch):
        import redis_manager
        redis_manager.redis_client = None
        monkeypatch.setattr(redis_manager.random, "random", lambda: 1.0)  # sampling gate never passes
        resp = client.post("/api/arduino/callback", json={"arduino_id": 14}, headers=LAMP_UA)
        assert resp.status_code == 200


@pytest.mark.integration
class TestStatusOverview:
    def test_status_overview_merges_redis_timestamps(self, client, lamp, fake_redis, db_session):
        from data_base import Arduino
        ard = db_session.query(Arduino).filter_by(arduino_id=14).one()
        ard.last_poll_time = datetime(2026, 1, 1, 0, 0, 0)
        db_session.commit()

        newer = datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)
        fake_redis.hset("arduino:last_seen", "14", newer.timestamp())

        body = client.get("/api/arduino/status").get_json()
        assert body["arduino_count"] == 1
        device = body["devices"][0]
        assert device["arduino_id"] == 14
        assert device["last_poll_time"].startswith("2026-01-15T10:00:00")

    def test_status_overview_keeps_db_time_when_redis_older(self, client, lamp, fake_redis, db_session):
        from data_base import Arduino
        ard = db_session.query(Arduino).filter_by(arduino_id=14).one()
        ard.last_poll_time = datetime(2026, 1, 15, 12, 0, 0)
        db_session.commit()
        fake_redis.hset("arduino:last_seen", "14", datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())

        device = client.get("/api/arduino/status").get_json()["devices"][0]
        assert device["last_poll_time"].startswith("2026-01-15T12:00:00")


@pytest.mark.integration
class TestDiscovery:
    def test_discovery_endpoint_returns_host(self, client):
        body = client.get("/api/discovery/server", headers={"Host": "lamps.example.com"}).get_json()
        assert body["api_server"] == "lamps.example.com"
        assert "arduino_data" in body["endpoints"]
