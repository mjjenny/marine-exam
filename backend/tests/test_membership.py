"""Membership lifecycle: expires_at, expired/revoked gates, revoke, check-expiries."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from app.extensions import db
from app.models import User
from app.models.user import MEMBERSHIP_DAYS, UserStatus


def test_approve_sets_365_day_expires_at(admin, user_factory, app):
    u = user_factory(status="pending", email="member@test.local")
    resp = admin.post(f"/api/admin/users/{u['id']}/approve")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "approved"
    assert body["expires_at"] is not None

    expires = datetime.fromisoformat(body["expires_at"])
    created = datetime.fromisoformat(body["created_at"])
    delta = expires - created
    assert timedelta(days=MEMBERSHIP_DAYS - 1) < delta <= timedelta(days=MEMBERSHIP_DAYS + 1)


def test_admin_users_have_no_expires_at(admin, user_factory):
    other = user_factory(status="approved", is_admin=True, email="admin2@test.local")
    users = admin.get("/api/admin/users").get_json()
    row = next(u for u in users if u["id"] == other["id"])
    assert row["expires_at"] is None


def test_expired_user_blocked_from_content(user_factory, login, content):
    past = datetime.now(timezone.utc) - timedelta(days=1)
    u = user_factory(
        status="expired",
        email="expired@test.local",
        expires_at=past,
    )
    client = login(u["email"], u["password"])
    resp = client.get("/api/subjects")
    assert resp.status_code == 403
    assert "expired" in resp.get_json()["error"].lower()


def test_revoked_user_blocked_from_content(user_factory, login, content):
    u = user_factory(status="revoked", email="revoked@test.local")
    client = login(u["email"], u["password"])
    resp = client.get("/api/subjects")
    assert resp.status_code == 403
    assert "revoked" in resp.get_json()["error"].lower()


def test_approved_member_still_reaches_content(user_factory, login, content):
    future = datetime.now(timezone.utc) + timedelta(days=200)
    u = user_factory(
        status="approved",
        email="active@test.local",
        expires_at=future,
    )
    client = login(u["email"], u["password"])
    assert client.get("/api/subjects").status_code == 200


def test_revoke_requires_admin(approved, user_factory):
    target = user_factory(status="approved", email="target@test.local")
    assert approved.post(f"/api/admin/users/{target['id']}/revoke").status_code == 403


def test_revoke_requires_auth(anon, user_factory):
    target = user_factory(status="approved", email="target2@test.local")
    assert anon.post(f"/api/admin/users/{target['id']}/revoke").status_code == 401


def test_admin_can_revoke_member(admin, user_factory, login, content):
    target = user_factory(status="approved", email="to-revoke@test.local")
    resp = admin.post(f"/api/admin/users/{target['id']}/revoke")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "revoked"

    member = login(target["email"], target["password"])
    assert member.get("/api/subjects").status_code == 403


def test_cannot_revoke_admin(admin, user_factory):
    other = user_factory(status="approved", is_admin=True, email="safe-admin@test.local")
    assert admin.post(f"/api/admin/users/{other['id']}/revoke").status_code == 400


def test_check_expiries_marks_overdue_and_sends_emails(app, user_factory, monkeypatch):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    overdue = user_factory(
        status="approved",
        email="overdue@test.local",
        expires_at=today_start - timedelta(days=2),
    )
    warn_30 = user_factory(
        status="approved",
        email="warn30@test.local",
        expires_at=today_start + timedelta(days=30, hours=12),
    )
    warn_7 = user_factory(
        status="approved",
        email="warn7@test.local",
        expires_at=today_start + timedelta(days=7, hours=12),
    )
    warn_1 = user_factory(
        status="approved",
        email="warn1@test.local",
        expires_at=today_start + timedelta(days=1, hours=12),
    )
    # Still active far in the future — should not be touched.
    user_factory(
        status="approved",
        email="safe@test.local",
        expires_at=today_start + timedelta(days=200),
    )

    expired_mock = MagicMock()
    reminder_mock = MagicMock()
    monkeypatch.setattr("app.cli.notify_membership_expired", expired_mock)
    monkeypatch.setattr("app.cli.notify_membership_expiry_reminder", reminder_mock)

    runner = app.test_cli_runner()
    result = runner.invoke(args=["check-expiries"])
    assert result.exit_code == 0, result.output
    assert "Expired 1" in result.output

    with app.app_context():
        status = db.session.get(User, overdue["id"]).status
        assert status == UserStatus.expired

    expired_mock.assert_called_once_with("overdue@test.local")
    reminder_days = sorted(call.args[1] for call in reminder_mock.call_args_list)
    assert reminder_days == [1, 7, 30]
    reminder_emails = {call.args[0] for call in reminder_mock.call_args_list}
    assert reminder_emails == {
        "warn30@test.local",
        "warn7@test.local",
        "warn1@test.local",
    }


def test_default_expires_helper_is_about_one_year():
    from app.models.user import _default_expires_at

    expires = _default_expires_at()
    delta = expires - datetime.now(timezone.utc)
    assert timedelta(days=MEMBERSHIP_DAYS - 1) < delta < timedelta(days=MEMBERSHIP_DAYS + 1)
