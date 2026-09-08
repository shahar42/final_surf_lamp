"""Cross-cutting security behaviour: headers, CSRF, auth decorators."""

import pytest

from security_config import SECURITY_HEADERS


@pytest.mark.integration
class TestHeaders:
    def test_security_headers_present_on_every_response(self, client, lamp):
        for path in ("/login", "/api/health", "/api/arduino/v3/14/data", "/api/beaches"):
            resp = client.get(path, headers={"User-Agent": "ESP32HTTPClient"})
            for header, value in SECURITY_HEADERS.items():
                assert resp.headers.get(header) == value, f"{path}: {header}"

    def test_csp_allows_only_known_cdns(self):
        csp = SECURITY_HEADERS["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "cdn.tailwindcss.com" in csp and "cdnjs.cloudflare.com" in csp
        assert "unsafe-eval" not in csp

    def test_session_cookie_flags(self, flask_app):
        assert flask_app.config["SESSION_COOKIE_HTTPONLY"] is True
        assert flask_app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
        # SESSION_COOKIE_SECURE is forced False by the test fixture; the source sets True.
        import inspect
        import config
        assert "SESSION_COOKIE_SECURE'] = True" in inspect.getsource(config.configure_app)


@pytest.mark.integration
class TestCsrf:
    """CSRF is form-level (FlaskForm), not app-level CSRFProtect: a missing token
    fails form validation and the page re-renders (200) without acting. JSON
    endpoints carry no CSRF token and rely on the SameSite=Lax session cookie,
    which browsers do not attach to cross-site POSTs."""

    def test_csrf_missing_token_does_not_log_in(self, client, flask_app, lamp):
        from ..conftest import PASSWORD
        flask_app.config["WTF_CSRF_ENABLED"] = True
        try:
            resp = client.post("/login", data={"email": lamp[1].email, "password": PASSWORD})
        finally:
            flask_app.config["WTF_CSRF_ENABLED"] = False
        assert resp.status_code == 200          # form re-rendered, not redirected to /dashboard
        with client.session_transaction() as s:
            assert "user_email" not in s

    def test_no_global_csrfprotect_is_a_known_choice(self, flask_app):
        assert "csrf" not in flask_app.extensions, "CSRFProtect registered: update this test and the JSON API tests"

    def test_csrf_token_rendered_in_login_form(self, client, flask_app):
        flask_app.config["WTF_CSRF_ENABLED"] = True
        try:
            resp = client.get("/login")
        finally:
            flask_app.config["WTF_CSRF_ENABLED"] = False
        assert b"csrf_token" in resp.data


@pytest.mark.integration
class TestDecorators:
    def test_login_required_redirects_with_flash(self, client):
        from ..conftest import flashes
        resp = client.get("/dashboard")
        assert resp.status_code == 302 and resp.headers["Location"].endswith("/login")
        assert any("log in" in m.lower() for m in flashes(client))

    def test_admin_required_redirects_normal_user_to_dashboard(self, client, lamp, login):
        from ..conftest import flashes
        login(lamp[1])
        resp = client.get("/admin/stats")
        assert resp.status_code == 302 and resp.headers["Location"].endswith("/dashboard")
        assert any("Admin access required" in m for m in flashes(client))

    def test_admin_required_with_stale_session_email(self, client):
        """Session names a user that no longer exists -> treated as non-admin."""
        with client.session_transaction() as s:
            s["user_email"] = "deleted@example.com"
            s["user_id"] = 999
        resp = client.get("/admin/stats")
        assert resp.status_code == 302 and resp.headers["Location"].endswith("/dashboard")
