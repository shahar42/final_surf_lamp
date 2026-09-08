"""
Integration tests for the admin blueprint: access control on every admin
route, broadcast lifecycle, fleet status, and the stats page.
"""

from datetime import datetime, timedelta, timezone

import pytest

ADMIN_ROUTES = [
    ("GET", "/admin/broadcast", None),
    ("POST", "/admin/broadcast/create", {"message": "hi", "duration": 2}),
    ("GET", "/admin/arduino-monitor", None),
    ("GET", "/admin/stats", None),
]


@pytest.fixture
def push(monkeypatch):
    """Record push broadcasts instead of calling pywebpush."""
    import blueprints.admin as admin_bp
    calls = []
    monkeypatch.setattr(admin_bp, "trigger_push_broadcast", lambda message, target_location=None: calls.append((message, target_location)) or 0)
    return calls


@pytest.fixture
def admin(make_user, make_location):
    make_location()
    return make_user(email="admin@example.com", username="admin", is_admin=True)


def call(client, method, path, payload):
    return client.post(path, json=payload) if method == "POST" else client.get(path)


@pytest.mark.integration
class TestAccessControl:
    @pytest.mark.parametrize("method,path,payload", ADMIN_ROUTES)
    def test_admin_routes_redirect_anonymous_to_login(self, client, method, path, payload):
        resp = call(client, method, path, payload)
        assert resp.status_code == 302 and resp.headers["Location"].endswith("/login")

    @pytest.mark.parametrize("method,path,payload", ADMIN_ROUTES)
    def test_admin_routes_redirect_normal_user_to_dashboard(self, client, lamp, login, method, path, payload):
        login(lamp[1])
        resp = call(client, method, path, payload)
        assert resp.status_code == 302 and resp.headers["Location"].endswith("/dashboard")

    def test_admin_pages_render_for_admin(self, client, admin, login):
        login(admin)
        assert client.get("/admin/broadcast").status_code == 200
        assert client.get("/admin/arduino-monitor").status_code == 200
        assert client.get("/admin/stats").status_code == 200

    def test_fleet_status_api_is_login_only_not_admin_only(self, client, lamp, login):
        """Pinned current behaviour: /api/admin/arduino-status is reachable by any
        logged-in user despite the /admin prefix. Tightening it is a product call."""
        login(lamp[1])
        assert client.get("/api/admin/arduino-status").status_code == 200
        client.get("/logout")
        assert client.get("/api/admin/arduino-status").status_code == 302


@pytest.mark.integration
class TestBroadcasts:
    def test_create_broadcast_saves_and_pushes(self, client, admin, login, push, db_session):
        from data_base import Broadcast
        login(admin)
        resp = client.post("/admin/broadcast/create", json={"message": "Big swell tomorrow", "duration": 5, "target_location": "all"})
        assert resp.status_code == 200 and resp.get_json()["success"] is True
        b = db_session.query(Broadcast).one()
        assert b.message == "Big swell tomorrow"
        assert b.target_location is None
        assert b.is_active is True
        assert b.expires_at - b.created_at >= timedelta(hours=4, minutes=59)
        assert push == [("Big swell tomorrow", None)]

    def test_create_broadcast_deactivates_previous(self, client, admin, login, push, db_session):
        from data_base import Broadcast
        login(admin)
        client.post("/admin/broadcast/create", json={"message": "first", "duration": 2})
        client.post("/admin/broadcast/create", json={"message": "second", "duration": 2})
        db_session.expire_all()
        active = db_session.query(Broadcast).filter_by(is_active=True).all()
        assert [b.message for b in active] == ["second"]

    def test_create_broadcast_validation(self, client, admin, login, push):
        from security_config import SecurityConfig
        login(admin)
        assert client.post("/admin/broadcast/create", json={"message": "   "}).status_code == 400
        assert client.post("/admin/broadcast/create", json={"message": "x" * (SecurityConfig.MAX_BROADCAST_MESSAGE_LENGTH + 1)}).status_code == 400
        assert client.post("/admin/broadcast/create", json={"message": "ok", "target_location": "Atlantis"}).status_code == 400
        assert push == []

    def test_create_broadcast_sanitizes_html(self, client, admin, login, push, db_session):
        from data_base import Broadcast
        login(admin)
        client.post("/admin/broadcast/create", json={"message": "<b>bold</b><script>x()</script>"})
        assert db_session.query(Broadcast).one().message == "boldx()"

    def test_targeted_broadcast_only_visible_at_that_beach(self, client, admin, login, push, make_user, make_location, db_session):
        make_location(name="Hilton Beach (Tel Aviv)")
        login(admin)
        client.post("/admin/broadcast/create", json={"message": "Hilton only", "target_location": "Hilton Beach (Tel Aviv)"})

        sdot_user = make_user(location="Sdot Yam")
        hilton_user = make_user(location="Hilton Beach (Tel Aviv)")

        login(sdot_user)
        assert client.get("/api/broadcasts").get_json()["broadcasts"] == []
        login(hilton_user)
        assert [b["message"] for b in client.get("/api/broadcasts").get_json()["broadcasts"]] == ["Hilton only"]

    def test_broadcast_dismiss_hides_for_user_only(self, client, admin, login, push, make_user):
        login(admin)
        client.post("/admin/broadcast/create", json={"message": "everyone"})
        alice, bob = make_user(), make_user()

        login(alice)
        bid = client.get("/api/broadcasts").get_json()["broadcasts"][0]["id"]
        assert client.post(f"/api/broadcasts/{bid}/dismiss").get_json()["success"] is True
        assert client.get("/api/broadcasts").get_json()["broadcasts"] == []
        # dismissing twice is idempotent
        assert client.post(f"/api/broadcasts/{bid}/dismiss").get_json()["message"] == "Already dismissed"

        login(bob)
        assert len(client.get("/api/broadcasts").get_json()["broadcasts"]) == 1

    def test_dismiss_unknown_broadcast_404(self, client, lamp, login):
        login(lamp[1])
        assert client.post("/api/broadcasts/999/dismiss").status_code == 404

    def test_expired_broadcast_not_listed(self, client, admin, login, push, db_session):
        from data_base import Broadcast
        login(admin)
        client.post("/admin/broadcast/create", json={"message": "old news"})
        b = db_session.query(Broadcast).one()
        b.expires_at = datetime.utcnow() - timedelta(minutes=1)
        db_session.commit()
        assert client.get("/api/broadcasts").get_json()["broadcasts"] == []

    def test_broadcast_rate_limit_10_per_hour(self, client, admin, login, push):
        from config import limiter
        login(admin)
        limiter.enabled = True
        limiter.reset()
        try:
            codes = [client.post("/admin/broadcast/create", json={"message": f"m{i}"}).status_code for i in range(11)]
        finally:
            limiter.enabled = False
            limiter.reset()
        assert codes[:10] == [200] * 10 and codes[10] == 429


@pytest.mark.integration
class TestFleetStatus:
    def test_arduino_status_api_merges_redis(self, client, lamp, login, fake_redis):
        login(lamp[1])
        fake_redis.hset("arduino:last_seen", "14", datetime.now(timezone.utc).timestamp())
        body = client.get("/api/admin/arduino-status").get_json()
        assert body["success"] is True
        assert body["summary"]["total"] == 1
        device = body["devices"][0]
        assert device["arduino_id"] == 14
        assert device["status"] == "active"
        assert device["username"] == lamp[1].username

    def test_arduino_status_api_never_when_no_poll(self, client, lamp, login, db_session):
        from data_base import Arduino
        ard = db_session.query(Arduino).filter_by(arduino_id=14).one()
        ard.last_poll_time = None
        db_session.commit()
        login(lamp[1])
        device = client.get("/api/admin/arduino-status").get_json()["devices"][0]
        assert device["status"] == "never"

    def test_arduino_status_api_flags_stale_location_data(self, client, make_location, make_user, make_arduino, login):
        from config import STALE_DATA_THRESHOLD
        loc = make_location(consecutive_identical_updates=STALE_DATA_THRESHOLD + 2)
        user = make_user(location=loc.location)
        make_arduino(14, user, loc.location)
        login(user)
        device = client.get("/api/admin/arduino-status").get_json()["devices"][0]
        assert device["staleness_warning"] is True


@pytest.mark.integration
class TestStats:
    def test_admin_stats_only_locations_with_arduinos(self, client, admin, login, make_location):
        """Regression for 33e45aa: beaches without lamps are not ranked."""
        make_location(name="Hilton Beach (Tel Aviv)", wave_height_m=3.0)  # no arduino here
        login(admin)
        resp = client.get("/admin/stats")
        assert resp.status_code == 200
        assert b"Hilton Beach (Tel Aviv)" not in resp.data
