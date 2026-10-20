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

    def test_add_arduino_by_mac(self, client, lamp, login, db_session):
        """Normal flow: paste the MAC from the lamp's WiFi setup page."""
        from data_base import Arduino
        login(lamp[1])
        resp = client.post("/add-arduino", json={"mac_address": "A4:CF:12:34:56:78", "location": "Sdot Yam"})
        assert resp.status_code == 200, resp.get_json()
        assert db_session.query(Arduino).filter_by(arduino_id="a4cf12345678").one().user_id == lamp[1].user_id

    def test_add_arduino_rejects_malformed_mac(self, client, lamp, login):
        login(lamp[1])
        resp = client.post("/add-arduino", json={"mac_address": "A4:CF:12:34:56", "location": "Sdot Yam"})
        assert resp.status_code == 400
        assert "MAC" in resp.get_json()["message"]

    def test_add_arduino_rejects_unparseable_identifier(self, client, lamp, login):
        """Neither a MAC nor a legacy number: refuse rather than store junk."""
        login(lamp[1])
        resp = client.post("/add-arduino", json={"arduino_id": "not-an-id", "location": "Sdot Yam"})
        assert resp.status_code == 400
        assert "MAC" in resp.get_json()["message"]

    def test_add_arduino_normalizes_mac_notation(self, client, lamp, login, db_session):
        from data_base import Arduino
        login(lamp[1])
        resp = client.post("/add-arduino", json={"mac_address": "a4-cf-12-34-56-78", "location": "Sdot Yam"})
        assert resp.status_code == 200, resp.get_json()
        assert db_session.query(Arduino).filter_by(arduino_id="a4cf12345678").one()

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

    def test_dashboard_renders_for_user(self, client, lamp, login, monkeypatch):
        monkeypatch.setenv("LINKED_LAMPS_FEATURE_ENABLED", "true")
        login(lamp[1])
        resp = client.get("/dashboard", headers=BROWSER_UA)
        assert resp.status_code == 200
        assert b"Sdot Yam" in resp.data          # user's location rendered
        assert b">14<" in resp.data              # linked lamp listed by its identifier

    def test_linked_lamps_hidden_by_default(self, client, lamp, login, monkeypatch):
        """Linked Lamps stays in code for future multi-lamp linking but is off
        unless LINKED_LAMPS_FEATURE_ENABLED is set."""
        monkeypatch.delenv("LINKED_LAMPS_FEATURE_ENABLED", raising=False)
        login(lamp[1])
        resp = client.get("/dashboard", headers=BROWSER_UA)
        assert resp.status_code == 200
        assert b"Linked Lamps" not in resp.data
        assert b'id="showAddArduinoBtn"' not in resp.data

    def test_dashboard_data_shows_fresh_conditions(self, lamp, flask_app):
        from blueprints.dashboard import _build_dashboard_data
        with flask_app.app_context():
            data, user = _build_dashboard_data(lamp[1].email)
        assert user.user_id == lamp[1].user_id
        assert data["conditions"]["wave_height_m"] == 1.2
        assert data["arduinos"][0]["arduino_id"] == "14"

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

    def test_dashboard_shows_the_mac_not_an_opaque_number(self, make_location, make_user, make_arduino, client, login, monkeypatch):
        """A MAC-identified lamp is listed by the address printed on its WiFi
        setup page, which is the only identifier the user has ever seen."""
        monkeypatch.setenv("LINKED_LAMPS_FEATURE_ENABLED", "true")
        loc = make_location()
        user = make_user(location=loc.location)
        make_arduino("A4:CF:12:34:56:78", user, loc.location)
        login(user)
        resp = client.get("/dashboard")
        assert b"A4:CF:12:34:56:78" in resp.data          # shown to the user
        # The stored form still reaches the page's JS config, which calls the
        # device API with it - and it must be QUOTED, or a MAC would parse as
        # an undefined JS identifier and break the LED visualization.
        assert b'arduinoId: "a4cf12345678"' in resp.data

    def test_dashboard_data_unknown_user(self, flask_app):
        from blueprints.dashboard import _build_dashboard_data
        with flask_app.app_context():
            assert _build_dashboard_data("ghost@example.com") == (None, None)

    def test_wifi_guide_renders_markdown(self, client, lamp, login):
        login(lamp[1])
        resp = client.get("/wifi-setup-guide")
        assert resp.status_code == 200
