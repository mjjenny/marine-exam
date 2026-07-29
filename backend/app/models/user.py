"""User table with the pending/approved/rejected/expired/revoked approval gate."""
import enum
from datetime import datetime, timedelta, timezone

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db

MEMBERSHIP_DAYS = 365


class UserStatus(str, enum.Enum):
    pending  = "pending"
    approved = "approved"
    rejected = "rejected"
    expired  = "expired"
    revoked  = "revoked"


def _default_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=MEMBERSHIP_DAYS)


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(db.Text, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(db.Text, nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        SAEnum(UserStatus, name="user_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=UserStatus.pending,
    )
    is_admin: Mapped[bool] = mapped_column(db.Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True), nullable=False, server_default=db.func.now()
    )
    # Admins have no expiry (NULL = never expires).
    expires_at: Mapped[datetime | None] = mapped_column(
        db.DateTime(timezone=True), nullable=True, default=None
    )

    __table_args__ = (
        Index("idx_users_status", "status"),
        Index("idx_users_expires_at", "expires_at"),
    )
