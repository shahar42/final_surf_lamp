"""
Integration tests for the auth blueprint: QR-gated registration, login,
logout, and the password reset token lifecycle.
"""

from datetime import timedelta

import pytest
from freezegun import freeze_time

from ..conftest import PASSWORD, flashes

MAX_ID = 16777215


def registration_form(arduino_id=14, **overrides):
    data = {
        "name": "Surf Fan",
        "email": "fan@example.com",
        "password": PASSWORD,
        "arduino_id": str(arduino_id),
        "location": "Sdot Yam",
        "sport_type": "surfing",
        "units": "meters",
    }
    data.update(overrides)
    return data


@pytest.mark.integration
class TestRegister:
    def test_register_requires_qr_id(self, client):
        resp = client.get("/register")
        assert resp.status_code == 200
        assert any("QR code" in m for m in flashes(client))

    def test_register_get_with_qr_prefills_id(self, client):
        resp = client.get("/register?id=6689108")
        assert resp.status_code == 200
        assert b'value="6689108"' in resp.data
        assert not flashes(client)

    def test_register_creates_user_arduino_location(self, client, db_session):
        from data_base import Arduino, Location, User

        resp = client.post("/register", data=registration_form(), follow_redirects=False)

        assert resp.status_code == 302 and resp.headers["Location"].endswith("/dashboard")
        user = db_session.query(User).filter_by(email="fan@example.com").one()
        assert user.username == "Surf Fan"
        assert user.location == "Sdot Yam"
        assert user.password_hash != PASSWORD
        ard = db_session.query(Arduino).filter_by(arduino_id=14).one()
        assert ard.user_id == user.user_id and ard.location == "Sdot Yam"
        loc = db_session.query(Location).filter_by(location="Sdot Yam").one()
        assert "marine-api.open-meteo.com" in loc.wave_api_url
        with client.session_transaction() as s:
            assert s["user_email"] == "fan@example.com"  # auto-login

    def test_register_duplicate_arduino_id_rejected(self, client, lamp, db_session):
        from data_base import User
        before = db_session.query(User).count()
        resp = client.post("/register", data=registration_form(arduino_id=14, email="second@example.com"))
        assert resp.status_code == 200  # re-rendered with error
        assert db_session.query(User).count() == before

    def test_register_duplicate_email_rejected(self, client, lamp, db_session):
        from data_base import Arduino
        resp = client.post("/register", data=registration_form(arduino_id=77, email=lamp[1].email))
        assert resp.status_code == 200
        assert db_session.query(Arduino).filter_by(arduino_id=77).first() is None

    def test_register_accepts_24bit_id(self, client, db_session):
        from data_base import Arduino
        client.post("/register", data=registration_form(arduino_id=MAX_ID))
        assert db_session.query(Arduino).filter_by(arduino_id=MAX_ID).one()

    def test_register_rejects_id_over_max(self, client, db_session):
        from data_base import User
        client.post("/register", data=registration_form(arduino_id=MAX_ID + 1))
        assert db_session.query(User).count() == 0
        assert any("Arduino Id" in m for m in flashes(client))

    def test_register_rejects_unknown_location(self, client, db_session):
        from data_base import User
        client.post("/register", data=registration_form(location="Atlantis"))
        assert db_session.query(User).count() == 0

    def test_register_redirects_logged_in_user(self, client, lamp, login):
        login(lamp[1])
        resp = client.get("/register?id=5")
        assert resp.status_code == 302 and resp.headers["Location"].endswith("/dashboard")


@pytest.mark.integration
class TestLogin:
    def test_login_success_sets_session(self, client, lamp):
        user = lamp[1]
        resp = client.post("/login", data={"email": user.email, "password": PASSWORD})
        assert resp.status_code == 302 and resp.headers["Location"].endswith("/dashboard")
        with client.session_transaction() as s:
            assert s["user_id"] == user.user_id
            assert s.permanent is False

    def test_login_is_case_insensitive_on_email(self, client, lamp):
        resp = client.post("/login", data={"email": lamp[1].email.upper(), "password": PASSWORD})
        assert resp.headers["Location"].endswith("/dashboard")

    def test_login_remember_me_makes_session_permanent(self, client, lamp):
        client.post("/login", data={"email": lamp[1].email, "password": PASSWORD, "remember_me": "y"})
        with client.session_transaction() as s:
            assert s.permanent is True

    def test_login_wrong_password(self, client, lamp):
        resp = client.post("/login", data={"email": lamp[1].email, "password": "nope-nope-nope"})
        assert resp.status_code == 302 and resp.headers["Location"].endswith("/login")
        with client.session_transaction() as s:
            assert "user_email" not in s
        assert any("Invalid email or password" in m for m in flashes(client))

    def test_login_unknown_email_same_message(self, client):
        """No account enumeration: unknown email and wrong password read the same."""
        client.post("/login", data={"email": "ghost@example.com", "password": PASSWORD})
        assert any("Invalid email or password" in m for m in flashes(client))

    def test_logout_clears_session(self, client, lamp, login):
        login(lamp[1])
        resp = client.get("/logout")
        assert resp.headers["Location"].endswith("/login")
        with client.session_transaction() as s:
            assert "user_email" not in s


@pytest.mark.integration
class TestPasswordReset:
    @pytest.fixture
    def sent(self, monkeypatch):
        """Capture the raw token instead of sending mail."""
        calls = []
        import blueprints.auth as auth_bp
        monkeypatch.setattr(auth_bp, "send_reset_email", lambda email, username, token: calls.append((email, token)))
        return calls

    def test_forgot_password_generic_message_for_unknown_email(self, client, sent, db_session):
        from data_base import PasswordResetToken
        resp = client.post("/forgot-password", data={"email": "ghost@example.com"})
        assert resp.headers["Location"].endswith("/login")
        assert any("If an account exists" in m for m in flashes(client))
        assert sent == []
        assert db_session.query(PasswordResetToken).count() == 0

    def test_forgot_password_known_email_creates_hashed_token(self, client, lamp, sent, db_session):
        import hashlib
        from data_base import PasswordResetToken

        client.post("/forgot-password", data={"email": lamp[1].email})

        assert len(sent) == 1
        email, token = sent[0]
        assert email == lamp[1].email
        row = db_session.query(PasswordResetToken).one()
        assert row.token_hash == hashlib.sha256(token.encode()).hexdigest()
        assert row.token_hash != token  # never stored raw

    def test_new_reset_request_invalidates_old_token(self, client, lamp, sent, db_session):
        import hashlib
        from data_base import PasswordResetToken
        client.post("/forgot-password", data={"email": lamp[1].email})
        client.post("/forgot-password", data={"email": lamp[1].email})
        assert len(sent) == 2
        db_session.expire_all()
        by_hash = {r.token_hash: r for r in db_session.query(PasswordResetToken).all()}
        assert len(by_hash) == 2
        first = by_hash[hashlib.sha256(sent[0][1].encode()).hexdigest()]
        second = by_hash[hashlib.sha256(sent[1][1].encode()).hexdigest()]
        assert first.is_invalidated is True
        assert second.is_invalidated is False

    def test_reset_changes_password_and_consumes_token(self, client, lamp, sent, db_session):
        from config import bcrypt
        from data_base import PasswordResetToken, User

        client.post("/forgot-password", data={"email": lamp[1].email})
        _, token = sent[0]

        resp = client.post(f"/reset-password/{token}", data={"new_password": "brand-new-password-1", "confirm_password": "brand-new-password-1"})
        assert resp.headers["Location"].endswith("/login")

        db_session.expire_all()  # drop the identity-map copy loaded by make_user
        user = db_session.query(User).filter_by(user_id=lamp[1].user_id).one()
        assert bcrypt.check_password_hash(user.password_hash, "brand-new-password-1")
        assert db_session.query(PasswordResetToken).one().used_at is not None

    def test_reset_token_single_use(self, client, lamp, sent):
        client.post("/forgot-password", data={"email": lamp[1].email})
        _, token = sent[0]
        form = {"new_password": "brand-new-password-1", "confirm_password": "brand-new-password-1"}
        client.post(f"/reset-password/{token}", data=form)
        resp = client.post(f"/reset-password/{token}", data=form)
        assert resp.headers["Location"].endswith("/forgot-password")
        assert any("Invalid or expired" in m for m in flashes(client))

    def test_reset_token_expires_after_20_minutes(self, client, lamp, sent):
        with freeze_time("2026-01-15 10:00:00") as clock:
            client.post("/forgot-password", data={"email": lamp[1].email})
            _, token = sent[0]
            clock.tick(timedelta(minutes=21))
            resp = client.post(f"/reset-password/{token}", data={"new_password": "brand-new-password-1", "confirm_password": "brand-new-password-1"})
        assert resp.headers["Location"].endswith("/forgot-password")

    def test_reset_mismatched_confirmation_rejected(self, client, lamp, sent, db_session):
        from data_base import PasswordResetToken
        client.post("/forgot-password", data={"email": lamp[1].email})
        _, token = sent[0]
        resp = client.post(f"/reset-password/{token}", data={"new_password": "brand-new-password-1", "confirm_password": "different"})
        assert resp.status_code == 200  # form re-rendered
        assert db_session.query(PasswordResetToken).one().used_at is None

    def test_bogus_token_rejected(self, client):
        resp = client.post("/reset-password/not-a-real-token", data={"new_password": "brand-new-password-1", "confirm_password": "brand-new-password-1"})
        assert resp.headers["Location"].endswith("/forgot-password")


@pytest.mark.integration
class TestLoginRateLimit:
    def test_login_rate_limit_10_per_minute(self, client, flask_app):
        from config import limiter
        limiter.enabled = True
        limiter.reset()
        try:
            codes = [client.post("/login", data={"email": "x@example.com", "password": "bad-bad-bad"}).status_code for _ in range(11)]
        finally:
            limiter.enabled = False
            limiter.reset()
        assert codes[:10] == [302] * 10
        assert codes[10] == 429
