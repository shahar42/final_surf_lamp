"""Integration tests for the dashboard blueprint."""

from datetime import datetime, timedelta, timezone

import pytest

from ..conftest import BROWSER_UA


@pytest.mark.integration
class TestAddArduino:
    def test_add_arduino_links_to_current_user(self, client, lamp, login, db_session):
        from data_base import Arduino
        login(lamp[1])
        resp = client.post("/add-arduino", json={"arduino_id": 6689108, "location": "Sdot Yam"})
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True
        ard = db_session.query(Arduino).filter_by(arduino_id=6689108).one()
        assert ard.user_id == lamp[1].user_id

    def test_add_arduino_returns_json_not_500(self, client, lamp, login):
        """Regression for 321e621: jsonify was not imported in this blueprint."""
        login(lamp[1])
        resp = client.post("/add-arduino", json={"arduino_id": "abc", "location": "Sdot Yam"})
        assert resp.status_code == 400
        assert resp.is_json and resp.get_json()["success"] is False

    @pytest.mark.parametrize("bad_id", [-5, 16777216])
    def test_add_arduino_rejects_out_of_range(self, client, lamp, login, bad_id):
        """Regression for the range guard added in 9790cc8."""
        login(lamp[1])
        resp = client.post("/add-arduino", json={"arduino_id": bad_id, "location": "Sdot Yam"})
        assert resp.status_code == 400
        assert "16777215" in resp.get_json()["message"]

    def test_add_arduino_rejects_zero(self, client, lamp, login):
        """0 is caught by the missing-field check (falsy), still a 400."""
        login(lamp[1])
        resp = client.post("/add-arduino", json={"arduino_id": 0, "location": "Sdot Yam"})
        assert resp.status_code == 400

    def test_add_arduino_missing_fields(self, client, lamp, login):
        login(lamp[1])
        assert client.post("/add-arduino", json={"arduino_id": 5}).status_code == 400
        assert client.post("/add-arduino", json={"location": "Sdot Yam"}).status_code == 400

    def test_add_arduino_duplicate_id(self, client, lamp, login):
        login(lamp[1])
        resp = client.post("/add-arduino", json={"arduino_id": 14, "location": "Sdot Yam"})
        assert resp.status_code == 400
        assert "already" in resp.get_json()["message"]

    def test_add_arduino_unknown_location(self, client, lamp, login):
        login(lamp[1])
        resp = client.post("/add-arduino", json={"arduino_id": 55, "location": "Atlantis"})
        assert resp.status_code == 400

    def test_add_arduino_requires_login(self, client, lamp):
        resp = client.post("/add-arduino", json={"arduino_id": 55, "location": "Sdot Yam"})
        assert resp.status_code == 302 and resp.headers["Location"].endswith("/login")


@pytest.mark.integration
class TestDashboardPage:
    def test_dashboard_requires_login(self, client):
        resp = client.get("/dashboard")
        assert resp.status_code == 302 and resp.headers["Location"].endswith("/login")

    def test_dashboard_renders_for_user(self, client, lamp, login):
        login(lamp[1])
        resp = client.get("/dashboard", headers=BROWSER_UA)
        assert resp.status_code == 200
        assert b"Sdot Yam" in resp.data          # user's location rendered
        assert b"#14" in resp.data               # linked lamp listed

    def test_dashboard_data_shows_fresh_conditions(self, lamp, flask_app):
        from blueprints.dashboard import _build_dashboard_data
        with flask_app.app_context():
            data, user = _build_dashboard_data(lamp[1].email)
        assert user.user_id == lamp[1].user_id
        assert data["conditions"]["wave_height_m"] == 1.2
        assert data["arduinos"][0]["arduino_id"] == 14

    def test_dashboard_hides_stale_conditions(self, make_location, make_user, make_arduino, flask_app):
        """Regression for 56f8803: conditions older than the online threshold are hidden."""
        from blueprints.dashboard import _build_dashboard_data
        from shared_config import LAMP_ONLINE_THRESHOLD_SECONDS
        stale = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=LAMP_ONLINE_THRESHOLD_SECONDS + 60)
        loc = make_location(last_updated=stale)
        user = make_user(location=loc.location)
        make_arduino(14, user, loc.location)
        with flask_app.app_context():
            data, _ = _build_dashboard_data(user.email)
        assert data["conditions"] is None

    def test_dashboard_data_unknown_user(self, flask_app):
        from blueprints.dashboard import _build_dashboard_data
        with flask_app.app_context():
            assert _build_dashboard_data("ghost@example.com") == (None, None)

    def test_wifi_guide_renders_markdown(self, client, lamp, login):
        login(lamp[1])
        resp = client.get("/wifi-setup-guide")
        assert resp.status_code == 200
