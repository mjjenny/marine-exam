"""Auth routes: signup, login, logout, current-user.

Uses Flask signed-session cookies. The SPA reaches these through the Vite /api proxy,
so requests are same-origin and cookies flow without extra CORS config.
"""
import re

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError

from ..auth import (
    current_user,
    hash_password,
    login_required,
    login_user,
    logout_user,
    validate_password,
    verify_password,
)
from ..extensions import db
from ..models import User
from ..services.email import notify_admin_new_signup, notify_password_reset
from ..services.tokens import make_reset_token, verify_reset_token

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _user_json(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "status": user.status.value,
        "is_admin": user.is_admin,
        "expires_at": user.expires_at.isoformat() if user.expires_at else None,
    }


@bp.post("/signup")
def signup():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not EMAIL_RE.match(email):
        return jsonify({"error": "a valid email is required"}), 400
    pw_error = validate_password(password)
    if pw_error:
        return jsonify({"error": pw_error}), 400

    user = User(email=email, password_hash=hash_password(password))
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "an account with that email already exists"}), 409

    notify_admin_new_signup(user.email)
    # Do not log the user in on signup — they remain pending until approved.
    return jsonify({"status": user.status.value, "message": "awaiting approval"}), 201


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = db.session.execute(
        db.select(User).filter_by(email=email)
    ).scalar_one_or_none()
    # Verify even on missing user to reduce timing signal, then fail uniformly.
    if user is None or not verify_password(password, user.password_hash):
        return jsonify({"error": "invalid email or password"}), 401

    login_user(user)
    return jsonify(_user_json(user)), 200


@bp.post("/logout")
def logout():
    logout_user()
    return "", 204


@bp.get("/me")
@login_required
def me():
    return jsonify(_user_json(current_user())), 200


@bp.post("/change-password")
@login_required
def change_password():
    """Let a logged-in user set a new password (requires current password)."""
    data = request.get_json(silent=True) or {}
    current = data.get("current_password") or ""
    new_password = data.get("new_password") or ""

    user = current_user()
    if not verify_password(current, user.password_hash):
        return jsonify({"error": "current password is incorrect"}), 400

    pw_error = validate_password(new_password)
    if pw_error:
        return jsonify({"error": pw_error}), 400

    user.password_hash = hash_password(new_password)
    db.session.commit()
    return jsonify({"message": "Password updated."}), 200


@bp.post("/forgot-password")
def forgot_password():
    """Email a time-limited reset link. Always returns the same response so it never
    reveals whether an email is registered."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    user = db.session.execute(
        db.select(User).filter_by(email=email)
    ).scalar_one_or_none()
    if user is not None:
        token = make_reset_token(user)
        base = (current_app.config.get("APP_BASE_URL") or request.host_url).rstrip("/")
        notify_password_reset(user.email, f"{base}/reset-password?token={token}")

    return jsonify(
        {"message": "If that email is registered, a reset link has been sent."}
    ), 200


@bp.post("/reset-password")
def reset_password():
    """Set a new password from a valid reset token."""
    data = request.get_json(silent=True) or {}
    token = data.get("token") or ""
    password = data.get("password") or ""

    user = verify_reset_token(token)
    if user is None:
        return jsonify(
            {"error": "This reset link is invalid or has expired. Please request a new one."}
        ), 400

    pw_error = validate_password(password)
    if pw_error:
        return jsonify({"error": pw_error}), 400

    user.password_hash = hash_password(password)
    db.session.commit()
    return jsonify({"message": "Your password has been reset. You can now log in."}), 200
