"""Moderation + versioning: suggested_edits, suggested_edit_sketches, answer_history."""
import enum
from datetime import datetime

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class SuggestedEditStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class SuggestedEdit(db.Model):
    __tablename__ = "suggested_edits"

    id: Mapped[int] = mapped_column(primary_key=True)
    # attaches to the answer, not one instance
    canonical_answer_id: Mapped[int] = mapped_column(
        ForeignKey("canonical_answers.id", ondelete="CASCADE"), nullable=False
    )
    submitted_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    suggested_text: Mapped[str] = mapped_column(db.Text, nullable=False)
    status: Mapped[SuggestedEditStatus] = mapped_column(
        SAEnum(
            SuggestedEditStatus,
            name="suggested_edit_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=SuggestedEditStatus.pending,
    )
    submitted_at: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True), nullable=False, server_default=db.func.now()
    )
    reviewed_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), nullable=True)

    sketches: Mapped[list["SuggestedEditSketch"]] = relationship(
        back_populates="suggested_edit", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_suggested_status", "status"),  # moderation queue
        Index("idx_suggested_canonical", "canonical_answer_id"),
    )


class SuggestedEditSketch(db.Model):
    __tablename__ = "suggested_edit_sketches"

    id: Mapped[int] = mapped_column(primary_key=True)
    suggested_edit_id: Mapped[int] = mapped_column(
        ForeignKey("suggested_edits.id", ondelete="CASCADE"), nullable=False
    )
    image_path: Mapped[str] = mapped_column(db.Text, nullable=False)  # object-storage path

    suggested_edit: Mapped["SuggestedEdit"] = relationship(back_populates="sketches")

    __table_args__ = (Index("idx_sketch_edit", "suggested_edit_id"),)


class AnswerHistory(db.Model):
    __tablename__ = "answer_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_answer_id: Mapped[int] = mapped_column(
        ForeignKey("canonical_answers.id", ondelete="CASCADE"), nullable=False
    )
    previous_text: Mapped[str] = mapped_column(db.Text, nullable=True)
    previous_sketch_refs: Mapped[list] = mapped_column(JSONB, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True), nullable=False, server_default=db.func.now()
    )

    __table_args__ = (Index("idx_history_canonical", "canonical_answer_id"),)
