"""Per-user study progress and bookmarks."""
from datetime import datetime

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db

# Allowed polymorphic content kinds for progress + bookmarks.
CONTENT_TYPES = frozenset({"subject", "topic", "question", "answer", "diet", "sketch"})


class UserProgress(db.Model):
    """Marks a content item as completed for a given user."""

    __tablename__ = "user_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content_type: Mapped[str] = mapped_column(db.Text, nullable=False)
    content_id: Mapped[int] = mapped_column(db.Integer, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True), nullable=False, server_default=db.func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "content_type", "content_id", name="uq_user_progress_item"
        ),
        Index("idx_user_progress_user", "user_id"),
        Index("idx_user_progress_content", "content_type", "content_id"),
    )


class Bookmark(db.Model):
    """Saved-for-later content item for a given user."""

    __tablename__ = "bookmarks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content_type: Mapped[str] = mapped_column(db.Text, nullable=False)
    content_id: Mapped[int] = mapped_column(db.Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True), nullable=False, server_default=db.func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "content_type", "content_id", name="uq_user_bookmark_item"
        ),
        Index("idx_bookmarks_user", "user_id"),
        Index("idx_bookmarks_content", "content_type", "content_id"),
    )
