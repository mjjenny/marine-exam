"""Auth + approval-gate flows."""


def test_signup_creates_pending_user(anon):
    resp = anon.post(
        "/api/auth/signup",
        json={"email": "new@test.local", "password": "Password1!"},
    )
    assert resp.status_code == 201
    assert resp.get_json()["status"] == "pending"


def test_signup_does_not_log_in(anon):
    anon.post("/api/auth/signup", json={"email": "new@test.local", "password": "Password1!"})
    # No session should have been established by signup.
    assert anon.get("/api/auth/me").status_code == 401


def test_signup_duplicate_email_conflicts(anon):
    payload = {"email": "dup@test.local", "password": "Password1!"}
    assert anon.post("/api/auth/signup", json=payload).status_code == 201
    assert anon.post("/api/auth/signup", json=payload).status_code == 409


def test_signup_rejects_short_password(anon):
    resp = anon.post("/api/auth/signup", json={"email": "a@b.co", "password": "short"})
    assert resp.status_code == 400


def test_signup_rejects_bad_email(anon):
    resp = anon.post("/api/auth/signup", json={"email": "notanemail", "password": "Password1!"})
    assert resp.status_code == 400


def test_signup_enforces_password_complexity(anon):
    # each of these fails exactly one rule (no upper / no lower / no digit / no special)
    for weak in ["password123", "PASSWORD1!", "Password!!", "Password11", "Aa1!"]:
        resp = anon.post("/api/auth/signup", json={"email": "weak@test.local", "password": weak})
        assert resp.status_code == 400, weak


def test_signup_accepts_complex_password(anon):
    resp = anon.post("/api/auth/signup", json={"email": "strong@test.local", "password": "Password1!"})
    assert resp.status_code == 201


def test_forgot_password_response_is_neutral(anon, user_factory):
    # Identical response whether or not the email is registered (no user enumeration).
    unknown = anon.post("/api/auth/forgot-password", json={"email": "nobody@test.local"})
    known = anon.post("/api/auth/forgot-password", json={"email": user_factory()["email"]})
    assert unknown.status_code == known.status_code == 200
    assert unknown.get_json() == known.get_json()


def _reset_token(app, email):
    from app.extensions import db
    from app.models import User
    from app.services.tokens import make_reset_token
    with app.app_context():
        return make_reset_token(
            db.session.execute(db.select(User).filter_by(email=email)).scalar_one()
        )


def test_reset_password_flow(app, anon, user_factory):
    u = user_factory(status="approved", password="OldPass1!")
    token = _reset_token(app, u["email"])

    assert anon.post("/api/auth/reset-password",
                     json={"token": token, "password": "NewPass1!"}).status_code == 200
    # new password works; old one no longer does
    assert anon.post("/api/auth/login",
                     json={"email": u["email"], "password": "NewPass1!"}).status_code == 200
    assert anon.post("/api/auth/login",
                     json={"email": u["email"], "password": "OldPass1!"}).status_code == 401
    # the token is single-use — it can't be replayed after the hash changed
    assert anon.post("/api/auth/reset-password",
                     json={"token": token, "password": "Another1!"}).status_code == 400


def test_reset_password_rejects_invalid_token(anon):
    resp = anon.post("/api/auth/reset-password", json={"token": "not-a-real-token", "password": "NewPass1!"})
    assert resp.status_code == 400


def test_reset_password_enforces_complexity(app, anon, user_factory):
    u = user_factory(password="OldPass1!")
    token = _reset_token(app, u["email"])
    resp = anon.post("/api/auth/reset-password", json={"token": token, "password": "weak"})
    assert resp.status_code == 400


def test_login_success_returns_user(user_factory, login):
    u = user_factory(status="approved")
    client = login(u["email"], u["password"])
    me = client.get("/api/auth/me").get_json()
    assert me["email"] == u["email"]
    assert me["status"] == "approved"
    assert me["is_admin"] is False


def test_login_wrong_password_unauthorized(user_factory, anon):
    u = user_factory(status="approved")
    resp = anon.post("/api/auth/login", json={"email": u["email"], "password": "wrongpass1"})
    assert resp.status_code == 401


def test_me_requires_authentication(anon):
    assert anon.get("/api/auth/me").status_code == 401


def test_logout_clears_session(approved):
    assert approved.get("/api/auth/me").status_code == 200
    assert approved.post("/api/auth/logout").status_code == 204
    assert approved.get("/api/auth/me").status_code == 401


def test_pending_user_can_log_in_but_is_not_approved(pending):
    # Login succeeds (valid credentials) but the account is still pending.
    assert pending.get("/api/auth/me").get_json()["status"] == "pending"
