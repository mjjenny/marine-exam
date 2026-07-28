"""Content tables: subjects, diets, topics, canonical_answers, question_instances."""
from sqlalchemy import ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class Subject(db.Model):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.Text, nullable=False)
    slug: Mapped[str] = mapped_column(db.Text, nullable=False, unique=True)
    # True only for EK Oral: a flat topic/search subject with no diet layer. Drives the
    # diet-vs-flat UI and excludes the diet-oriented topic tab/view. Explicit (not
    # derived from diet existence) so empty diet-based subjects still present correctly.
    is_oral: Mapped[bool] = mapped_column(
        db.Boolean, nullable=False, default=False, server_default=db.text("false")
    )

    diets: Mapped[list["Diet"]] = relationship(back_populates="subject", cascade="all, delete-orphan")
    topics: Mapped[list["Topic"]] = relationship(back_populates="subject", cascade="all, delete-orphan")
    answers: Mapped[list["CanonicalAnswer"]] = relationship(
        back_populates="subject", cascade="all, delete-orphan"
    )


class Diet(db.Model):
    __tablename__ = "diets"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(db.Text, nullable=False)  # "July 2025"
    date: Mapped[object] = mapped_column(db.Date, nullable=True)
    sort_order: Mapped[int] = mapped_column(db.Integer, nullable=False, default=0)

    subject: Mapped["Subject"] = relationship(back_populates="diets")
    question_instances: Mapped[list["QuestionInstance"]] = relationship(back_populates="diet")

    __table_args__ = (Index("idx_diets_subject", "subject_id", db.text("sort_order DESC")),)


class Topic(db.Model):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(db.Text, nullable=False)

    subject: Mapped["Subject"] = relationship(back_populates="topics")

    __table_args__ = (Index("idx_topics_subject", "subject_id"),)


class CanonicalAnswer(db.Model):
    __tablename__ = "canonical_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="SET NULL"), nullable=True
    )
    # Stable reference key for seed/migration (e.g. imported question banks). Nullable
    # for hand-authored answers; unique when set.
    slug: Mapped[str] = mapped_column(db.Text, nullable=True, unique=True)
    # Canonical question title. Lives on the answer so it renders regardless of whether
    # the answer has any question_instances (occurrences).
    title: Mapped[str] = mapped_column(db.Text, nullable=True)
    # Mark total for the question, where known. Nullable: some imported questions have
    # an unverified original wording and no confirmed mark total.
    marks: Mapped[int] = mapped_column(db.Integer, nullable=True)
    # Verbatim "QUESTION AS SET" wording (the exact exam question incl. its (a)/(b) parts
    # and marks). Lives on the answer — one canonical question per entry. Nullable:
    # hand-authored / reference answers may have no set question.
    question_as_set: Mapped[str] = mapped_column(db.Text, nullable=True)
    answer_text: Mapped[str] = mapped_column(db.Text, nullable=False, default="")
    # array of stored-image references, e.g. [{"path": "...", "caption": "..."}]
    sketch_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    subject: Mapped["Subject"] = relationship(back_populates="answers")
    topic: Mapped["Topic"] = relationship()
    question_instances: Mapped[list["QuestionInstance"]] = relationship(
        back_populates="canonical_answer", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_canonical_subject", "subject_id"),
        Index("idx_canonical_topic", "topic_id"),
    )


class QuestionInstance(db.Model):
    __tablename__ = "question_instances"

    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_answer_id: Mapped[int] = mapped_column(
        ForeignKey("canonical_answers.id", ondelete="CASCADE"), nullable=False
    )
    # NULL for every EK Oral row (no diet layer)
    diet_id: Mapped[int] = mapped_column(
        ForeignKey("diets.id", ondelete="SET NULL"), nullable=True
    )
    question_number: Mapped[str] = mapped_column(db.Text, nullable=True)
    question_text_as_asked: Mapped[str] = mapped_column(db.Text, nullable=False)
    examiner_feedback_text: Mapped[str] = mapped_column(db.Text, nullable=True)
    # Per-sitting mark data and provenance (from imported question banks). Nullable:
    # not every sitting has a confirmed mark total / breakdown.
    total_marks: Mapped[int] = mapped_column(db.Integer, nullable=True)
    marks_parts: Mapped[list] = mapped_column(JSONB, nullable=True)  # e.g. ["5", "5"]
    # Confidence/provenance tag, e.g. verified_catalog / confirmed_via_screenshot_repeat_history
    source: Mapped[str] = mapped_column(db.Text, nullable=True)

    canonical_answer: Mapped["CanonicalAnswer"] = relationship(back_populates="question_instances")
    diet: Mapped["Diet"] = relationship(back_populates="question_instances")

    __table_args__ = (
        Index("idx_qi_canonical", "canonical_answer_id"),  # "also asked in" lookup
        Index("idx_qi_diet", "diet_id"),
    )
