"""Integration tests for the public, CDN-cacheable location conditions endpoint."""

import pytest


@pytest.mark.integration
class TestPublicConditions:
    def test_public_conditions_no_auth(self, client, lamp):
        resp = client.get("/api/locations/Sdot Yam/conditions")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["location"] == "Sdot Yam"
        assert body["wave_height_cm"] == 120
        assert body["wave_period_s"] == 8.0
        assert body["wind_speed_mps"] == 5
        assert body["wind_direction_deg"] == 180
        assert body["data_available"] is True
        assert "sunset_animation" in body and "day_of_year" in body

    def test_public_conditions_cache_control_header(self, client, lamp):
        resp = client.get("/api/locations/Sdot Yam/conditions")
        assert resp.headers["Cache-Control"] == "public, max-age=300"
        assert "Accept-Encoding" in resp.headers.get("Vary", "")

    def test_public_conditions_unknown_404(self, client):
        resp = client.get("/api/locations/Atlantis/conditions")
        assert resp.status_code == 404

    def test_public_conditions_no_user_fields(self, client, lamp):
        """Shared by every lamp at the beach; must never leak an owner's settings."""
        body = client.get("/api/locations/Sdot Yam/conditions").get_json()
        for forbidden in ("wave_threshold_cm", "wind_speed_threshold_knots", "quiet_hours_active",
                          "off_hours_active", "brightness_multiplier", "led_theme", "email", "username"):
            assert forbidden not in body, forbidden

    def test_public_conditions_location_with_parentheses(self, client, make_location):
        make_location(name="Hilton Beach (Tel Aviv)")
        resp = client.get("/api/locations/Hilton Beach (Tel Aviv)/conditions")
        assert resp.status_code == 200
        assert resp.get_json()["location"] == "Hilton Beach (Tel Aviv)"

    def test_public_conditions_empty_location_row(self, client, make_location):
        make_location(name="Empty Beach", wave_height_m=None, wave_period_s=None, wind_speed_mps=None, wind_direction_deg=None)
        body = client.get("/api/locations/Empty Beach/conditions").get_json()
        assert body["data_available"] is False
        assert body["wave_height_cm"] == 0
