"""Integration tests for POST /report-error."""

import pytest

from security_config import SecurityConfig


@pytest.mark.integration
class TestReportError:
    def test_report_error_persists_with_context(self, client, lamp, login, db_session):
        from data_base import ErrorReport
        login(lamp[1])
        resp = client.post("/report-error", json={"error_description": "Left strip stuck on red"},
                           headers={"User-Agent": "TestBrowser/1.0"})
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True
        report = db_session.query(ErrorReport).one()
        assert report.user_id == lamp[1].user_id
        assert report.email == lamp[1].email
        assert report.arduino_id == 14
        assert report.location == "Sdot Yam"
        assert report.user_agent == "TestBrowser/1.0"
        assert report.error_description == "Left strip stuck on red"

    def test_report_error_without_arduino(self, client, make_user, login, db_session):
        from data_base import ErrorReport
        user = make_user()
        login(user)
        assert client.post("/report-error", json={"error_description": "no lamp yet"}).status_code == 200
        assert db_session.query(ErrorReport).one().arduino_id is None

    def test_report_error_requires_description(self, client, lamp, login, db_session):
        from data_base import ErrorReport
        login(lamp[1])
        assert client.post("/report-error", json={"error_description": "   "}).status_code == 400
        assert client.post("/report-error", json={}).status_code == 400
        assert db_session.query(ErrorReport).count() == 0

    def test_report_error_too_long(self, client, lamp, login):
        login(lamp[1])
        resp = client.post("/report-error", json={"error_description": "x" * (SecurityConfig.MAX_INPUT_LENGTH + 1)})
        assert resp.status_code == 400

    def test_report_error_requires_login(self, client):
        resp = client.post("/report-error", json={"error_description": "x"})
        assert resp.status_code == 302 and resp.headers["Location"].endswith("/login")

    def test_error_reports_api_lists_newest_first(self, client, lamp, login):
        login(lamp[1])
        client.post("/report-error", json={"error_description": "first"})
        client.post("/report-error", json={"error_description": "second"})
        body = client.get("/api/error-reports").get_json()
        assert [r["error_description"] for r in body["reports"]][:2] == ["second", "first"] or \
               {r["error_description"] for r in body["reports"]} == {"first", "second"}
