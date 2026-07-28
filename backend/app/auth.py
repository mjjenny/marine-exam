"""Authentication helpers: password hashing, session access, route guards."""
from functools import wraps

import bcrypt
from flask import g, jsonify, session

from .extensions import db
from .models import User
from .models.user import UserStatus

SESSION_KEY = "user_id"

# bcrypt hashes at most the first 72 bytes of the input; truncate defensively so
# very long inputs don't raise instead of hashing.
_BCRYPT_MAX_BYTES = 72


def _encode(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_encode(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_encode(password), password_hash.encode("utf-8"))
    except ValueError:
        return False


PASSWORD_MIN_LENGTH = 8


def validate_password(password: str) -> str | None:
    """Return a human-readable error if the password fails the complexity policy,
    else None. Policy: >= 8 chars with at least one uppercase, lowercase, digit and
    special character. Used for signup and password reset."""
    pw = password or ""
    missing = []
    if len(pw) < PASSWORD_MIN_LENGTH:
        missing.append(f"at least {PASSWORD_MIN_LENGTH} characters")
    if not any(c.isupper() for c in pw):
        missing.append("an uppercase letter")
    if not any(c.islower() for c in pw):
        missing.append("a lowercase letter")
    if not any(c.isdigit() for c in pw):
        missing.append("a number")
    if not any((not c.isalnum()) and (not c.isspace()) for c in pw):
        missing.append("a special character")
    if missing:
        return "Password must contain " + ", ".join(missing) + "."
    return None


def login_user(user: User) -> None:
    session[SESSION_KEY] = user.id
    session.permanent = True


def logout_user() -> None:
    session.pop(SESSION_KEY, None)


def current_user() -> User | None:
    """Return the logged-in User (cached on g for the request), or None."""
    if "current_user" not in g:
        user_id = session.get(SESSION_KEY)
        g.current_user = (
            db.session.get(User, user_id) if user_id is not None else None
        )
    return g.current_user


def _error(message: str, status: int):
    return jsonify({"error": message}), status


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            return _error("authentication required", 401)
        return fn(*args, **kwargs)

    return wrapper


def approved_required(fn):
    """Gate: a logged-in user whose status is 'approved'. Use on all content routes."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            return _error("authentication required", 401)
        if user.status != UserStatus.approved:
            return _error("account not approved", 403)
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            return _error("authentication required", 401)
        if not user.is_admin:
            return _error("admin access required", 403)
        return fn(*args, **kwargs)

    return wrapper
