"""
Integration tests for the web-push blueprint. pywebpush is replaced with a
recorder; the VAPID key path is bypassed with a dummy PEM.
"""

import pytest

SUB = {"endpoint": "https://push.example/abc", "keys": {"p256dh": "P", "auth": "A"}}


@pytest.fixture
def webpush(monkeypatch):
    """Record webpush calls; raise WebPushException with a given status for chosen endpoints."""
    import blueprints.notifications as notif
    from pywebpush import WebPushException

    state = {"calls": [], "fail": {}}  # fail: endpoint -> status_code or Exception

    class Resp:
        def __init__(self, code):
            self.status_code = code

    def fake_webpush(subscription_info, data, vapid_private_key, vapid_claims):
        endpoint = subscription_info["endpoint"]
        state["calls"].append(endpoint)
        fail = state["fail"].get(endpoint)
        if isinstance(fail, int):
            raise WebPushException("push failed", response=Resp(fail))
        if isinstance(fail, Exception):
            raise fail

    monkeypatch.setattr(notif, "webpush", fake_webpush)
    monkeypatch.setattr(notif, "get_private_key_content", lambda: "-----BEGIN PRIVATE KEY-----\nAAAA\n-----END PRIVATE KEY-----")
    return state


def subscribe_user(db_session, user, endpoint):
    from data_base import NotificationSubscription
    db_session.add(NotificationSubscription(user_id=user.user_id, endpoint=endpoint, p256dh="P", auth="A"))
    db_session.commit()


@pytest.mark.integration
class TestSubscribe:
    def test_subscribe_requires_login(self, client):
        assert client.post("/notifications/subscribe", json=SUB).status_code == 401

    def test_subscribe_stores_subscription(self, client, lamp, login, db_session):
        from data_base import NotificationSubscription
        login(lamp[1])
        resp = client.post("/notifications/subscribe", json=SUB)
        assert resp.status_code == 201
        row = db_session.query(NotificationSubscription).one()
        assert (row.user_id, row.endpoint, row.p256dh, row.auth) == (lamp[1].user_id, SUB["endpoint"], "P", "A")

    def test_subscribe_idempotent_same_endpoint_updates_keys(self, client, lamp, login, db_session):
        from data_base import NotificationSubscription
        login(lamp[1])
        client.post("/notifications/subscribe", json=SUB)
        client.post("/notifications/subscribe", json={**SUB, "keys": {"p256dh": "P2", "auth": "A2"}})
        db_session.expire_all()
        rows = db_session.query(NotificationSubscription).all()
        assert len(rows) == 1 and rows[0].p256dh == "P2"

    @pytest.mark.parametrize("bad", [{}, {"endpoint": "x"}, {"endpoint": "x", "keys": {"p256dh": "P"}}])
    def test_subscribe_rejects_incomplete_payload(self, client, lamp, login, bad):
        login(lamp[1])
        assert client.post("/notifications/subscribe", json=bad).status_code == 400

    def test_vapid_public_key_endpoint(self, client):
        body = client.get("/notifications/vapid-public-key").get_json()
        assert body["publicKey"].startswith("B") and len(body["publicKey"]) > 80


@pytest.mark.integration
class TestPushBroadcast:
    def test_push_sends_to_every_subscription(self, flask_app, lamp, make_user, db_session, webpush):
        from blueprints.notifications import trigger_push_broadcast
        other = make_user()
        subscribe_user(db_session, lamp[1], "https://push.example/1")
        subscribe_user(db_session, other, "https://push.example/2")
        with flask_app.app_context():
            sent = trigger_push_broadcast("hello")
        assert sent == 2
        assert set(webpush["calls"]) == {"https://push.example/1", "https://push.example/2"}

    def test_push_broadcast_filters_by_location(self, flask_app, make_user, make_location, db_session, webpush):
        from blueprints.notifications import trigger_push_broadcast
        make_location(name="Hilton Beach (Tel Aviv)")
        sdot = make_user(location="Sdot Yam")
        hilton = make_user(location="Hilton Beach (Tel Aviv)")
        subscribe_user(db_session, sdot, "https://push.example/sdot")
        subscribe_user(db_session, hilton, "https://push.example/hilton")
        with flask_app.app_context():
            sent = trigger_push_broadcast("swell", target_location="Hilton Beach (Tel Aviv)")
        assert sent == 1
        assert webpush["calls"] == ["https://push.example/hilton"]

    @pytest.mark.parametrize("status", [403, 404, 410])
    def test_push_gone_statuses_delete_subscription(self, flask_app, lamp, db_session, webpush, status):
        from blueprints.notifications import trigger_push_broadcast
        from data_base import NotificationSubscription
        subscribe_user(db_session, lamp[1], "https://push.example/dead")
        webpush["fail"]["https://push.example/dead"] = status
        with flask_app.app_context():
            sent = trigger_push_broadcast("x")
        assert sent == 0
        db_session.expire_all()
        assert db_session.query(NotificationSubscription).count() == 0

    def test_push_other_error_keeps_subscription(self, flask_app, lamp, db_session, webpush):
        from blueprints.notifications import trigger_push_broadcast
        from data_base import NotificationSubscription
        subscribe_user(db_session, lamp[1], "https://push.example/flaky")
        webpush["fail"]["https://push.example/flaky"] = 500
        with flask_app.app_context():
            trigger_push_broadcast("x")
        assert db_session.query(NotificationSubscription).count() == 1

    def test_push_without_private_key_sends_nothing(self, flask_app, lamp, db_session, webpush, monkeypatch):
        import blueprints.notifications as notif
        monkeypatch.setattr(notif, "get_private_key_content", lambda: None)
        subscribe_user(db_session, lamp[1], "https://push.example/1")
        with flask_app.app_context():
            assert notif.trigger_push_broadcast("x") == 0
        assert webpush["calls"] == []


@pytest.mark.integration
class TestSendTestEndpoint:
    def test_send_test_requires_admin(self, client, lamp, login, webpush):
        """A push to every subscriber must not be triggerable anonymously or by any user."""
        assert client.post("/notifications/send-test", json={"message": "x"}).status_code == 302
        login(lamp[1])
        resp = client.post("/notifications/send-test", json={"message": "x"})
        assert resp.status_code == 302 and resp.headers["Location"].endswith("/dashboard")
        assert webpush["calls"] == []

    def test_send_test_as_admin(self, client, make_user, make_location, login, db_session, webpush):
        make_location()
        admin = make_user(is_admin=True)
        subscribe_user(db_session, admin, "https://push.example/admin")
        login(admin)
        body = client.post("/notifications/send-test", json={"message": "ping"}).get_json()
        assert body["sent_count"] == 1
