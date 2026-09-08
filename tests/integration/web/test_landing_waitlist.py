"""
Integration tests for the public landing/waitlist routes. The Google Sheets
backend and the confirmation email are replaced with recorders.
"""

import pytest

from ..conftest import flashes

FORM = {"first_name": "Dana", "last_name": "Levi", "email": "dana@example.com", "phone": "050-0000000"}


@pytest.fixture
def sheets(monkeypatch):
    """Fake add_to_waitlist/get_waitlist_count and capture confirmation emails."""
    import blueprints.landing as landing

    state = {"rows": [], "emails": [], "fail_with": None}

    def add_to_waitlist(first_name, last_name, email, phone=None, ip_address=None, user_agent=None):
        if state["fail_with"]:
            return False, state["fail_with"], None
        state["rows"].append(dict(first_name=first_name, last_name=last_name, email=email, phone=phone, ip=ip_address, ua=user_agent))
        return True, "ok", len(state["rows"])

    monkeypatch.setattr(landing, "add_to_waitlist", add_to_waitlist)
    monkeypatch.setattr(landing, "get_waitlist_count", lambda: len(state["rows"]))
    monkeypatch.setattr(landing, "send_waitlist_confirmation", lambda email, first_name, position: state["emails"].append((email, first_name, position)))
    return state


@pytest.mark.integration
class TestWaitlist:
    def test_waitlist_form_renders_with_count(self, client, sheets):
        assert client.get("/waitlist").status_code == 200

    def test_waitlist_submit_appends_row_and_sends_confirmation(self, client, sheets):
        resp = client.post("/waitlist/submit", data=FORM, headers={"User-Agent": "TestBrowser"})
        assert resp.status_code == 200
        assert b"Dana" in resp.data  # confirmation page
        assert sheets["rows"] == [dict(first_name="Dana", last_name="Levi", email="dana@example.com",
                                       phone="050-0000000", ip="127.0.0.1", ua="TestBrowser")]
        assert sheets["emails"] == [("dana@example.com", "Dana", 1)]

    def test_waitlist_submit_strips_whitespace_and_blank_phone(self, client, sheets):
        client.post("/waitlist/submit", data={**FORM, "first_name": "  Dana ", "phone": "  "})
        assert sheets["rows"][0]["first_name"] == "Dana"
        assert sheets["rows"][0]["phone"] is None

    @pytest.mark.parametrize("missing", ["first_name", "last_name", "email"])
    def test_waitlist_missing_required_field(self, client, sheets, missing):
        data = {**FORM, missing: ""}
        resp = client.post("/waitlist/submit", data=data)
        assert resp.status_code == 302 and resp.headers["Location"].endswith("/waitlist")
        assert sheets["rows"] == []
        assert any("required" in m for m in flashes(client))

    def test_waitlist_invalid_email(self, client, sheets):
        resp = client.post("/waitlist/submit", data={**FORM, "email": "not-an-email"})
        assert resp.headers["Location"].endswith("/waitlist")
        assert sheets["rows"] == [] and sheets["emails"] == []

    def test_waitlist_backend_failure_flashes_message(self, client, sheets):
        sheets["fail_with"] = "Email already on the waitlist"
        resp = client.post("/waitlist/submit", data=FORM)
        assert resp.headers["Location"].endswith("/waitlist")
        assert any("already on the waitlist" in m for m in flashes(client))
        assert sheets["emails"] == []

    def test_waitlist_rate_limit_3_per_hour(self, client, sheets):
        from config import limiter
        limiter.enabled = True
        limiter.reset()
        try:
            codes = [client.post("/waitlist/submit", data=FORM).status_code for _ in range(4)]
        finally:
            limiter.enabled = False
            limiter.reset()
        assert codes[:3] == [200, 200, 200]
        assert codes[3] == 429


@pytest.mark.integration
class TestLandingStatic:
    def test_privacy_page(self, client):
        assert client.get("/privacy").status_code == 200

    def test_legal_pages(self, client):
        for path in ("/privacy-policy", "/privacy-policy-he", "/terms-of-service", "/terms-of-service-he", "/warranty", "/accessibility-statement"):
            assert client.get(path).status_code == 200, path

    def test_root_redirects_to_dashboard(self, client):
        resp = client.get("/")
        assert resp.status_code == 302 and resp.headers["Location"].endswith("/dashboard")
