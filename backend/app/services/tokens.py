"""Signed, time-limited tokens for the password-reset flow.

Stateless — uses itsdangerous (a Flask dependency) with the app SECRET_KEY, so no
database columns or migration are required. The token is bound to the user's current
password hash, which makes it single-use: once the password changes the old token no
longer validates.
"""
from flask import current_app
from itsdangerous import BadData, URLSafeTimedSerializer

from ..extensions import db
from ..models import User

_RESET_SALT = "password-reset"
RESET_TOKEN_MAX_AGE = 3600  # seconds — reset links are valid for 1 hour


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=_RESET_SALT)


def make_reset_token(user: User) -> str:
    return _serializer().dumps({"uid": user.id, "pw": user.password_hash[-16:]})


def verify_reset_token(token: str, max_age: int = RESET_TOKEN_MAX_AGE) -> User | None:
    """Return the User for a valid, unexpired, unused token, or None."""
    try:
        data = _serializer().loads(token or "", max_age=max_age)
    except BadData:  # bad signature, expired, or malformed
        return None
    user = db.session.get(User, data.get("uid"))
    if user is None or data.get("pw") != user.password_hash[-16:]:
        return None
    return user
