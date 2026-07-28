"""initial schema — nine tables + two enums

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


user_status = postgresql.ENUM(
    "pending", "approved", "rejected", name="user_status", create_type=False
)
suggested_edit_status = postgresql.ENUM(
    "pending", "approved", "rejected", name="suggested_edit_status", create_type=False
)


def upgrade():
    bind = op.get_bind()
    user_status.create(bind, checkfirst=True)
    suggested_edit_status.create(bind, checkfirst=True)

    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
    )

    op.create_table(
        "diets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "subject_id",
            sa.Integer(),
            sa.ForeignKey("subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("date", sa.Date(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "idx_diets_subject", "diets", ["subject_id", sa.text("sort_order DESC")]
    )

    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "subject_id",
            sa.Integer(),
            sa.ForeignKey("subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
    )
    op.create_index("idx_topics_subject", "topics", ["subject_id"])

    op.create_table(
        "canonical_answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "subject_id",
            sa.Integer(),
            sa.ForeignKey("subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "topic_id",
            sa.Integer(),
            sa.ForeignKey("topics.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("answer_text", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "sketch_refs",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.create_index("idx_canonical_subject", "canonical_answers", ["subject_id"])
    op.create_index("idx_canonical_topic", "canonical_answers", ["topic_id"])

    op.create_table(
        "question_instances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "canonical_answer_id",
            sa.Integer(),
            sa.ForeignKey("canonical_answers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "diet_id",
            sa.Integer(),
            sa.ForeignKey("diets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("question_number", sa.Text(), nullable=True),
        sa.Column("question_text_as_asked", sa.Text(), nullable=False),
        sa.Column("examiner_feedback_text", sa.Text(), nullable=True),
    )
    op.create_index(
        "idx_qi_canonical", "question_instances", ["canonical_answer_id"]
    )
    op.create_index("idx_qi_diet", "question_instances", ["diet_id"])

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "status", user_status, nullable=False, server_default="pending"
        ),
        sa.Column(
            "is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_users_status", "users", ["status"])

    op.create_table(
        "suggested_edits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "canonical_answer_id",
            sa.Integer(),
            sa.ForeignKey("canonical_answers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "submitted_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("suggested_text", sa.Text(), nullable=False),
        sa.Column(
            "status",
            suggested_edit_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_suggested_status", "suggested_edits", ["status"])
    op.create_index(
        "idx_suggested_canonical", "suggested_edits", ["canonical_answer_id"]
    )

    op.create_table(
        "suggested_edit_sketches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "suggested_edit_id",
            sa.Integer(),
            sa.ForeignKey("suggested_edits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("image_path", sa.Text(), nullable=False),
    )
    op.create_index(
        "idx_sketch_edit", "suggested_edit_sketches", ["suggested_edit_id"]
    )

    op.create_table(
        "answer_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "canonical_answer_id",
            sa.Integer(),
            sa.ForeignKey("canonical_answers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("previous_text", sa.Text(), nullable=True),
        sa.Column("previous_sketch_refs", postgresql.JSONB(), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_history_canonical", "answer_history", ["canonical_answer_id"])


def downgrade():
    op.drop_table("answer_history")
    op.drop_table("suggested_edit_sketches")
    op.drop_table("suggested_edits")
    op.drop_table("users")
    op.drop_table("question_instances")
    op.drop_table("canonical_answers")
    op.drop_table("topics")
    op.drop_table("diets")
    op.drop_table("subjects")

    bind = op.get_bind()
    suggested_edit_status.drop(bind, checkfirst=True)
    user_status.drop(bind, checkfirst=True)
