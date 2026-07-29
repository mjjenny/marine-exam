"""Add user_progress and bookmarks tables

Revision ID: 0009_user_progress_bookmarks
Revises: 0008_user_expires_revoked
Create Date: 2026-07-29
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_user_progress_bookmarks"
down_revision = "0008_user_expires_revoked"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "user_id", "content_type", "content_id", name="uq_user_progress_item"
        ),
    )
    op.create_index("idx_user_progress_user", "user_progress", ["user_id"])
    op.create_index(
        "idx_user_progress_content", "user_progress", ["content_type", "content_id"]
    )

    op.create_table(
        "bookmarks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "user_id", "content_type", "content_id", name="uq_user_bookmark_item"
        ),
    )
    op.create_index("idx_bookmarks_user", "bookmarks", ["user_id"])
    op.create_index(
        "idx_bookmarks_content", "bookmarks", ["content_type", "content_id"]
    )


def downgrade():
    op.drop_index("idx_bookmarks_content", table_name="bookmarks")
    op.drop_index("idx_bookmarks_user", table_name="bookmarks")
    op.drop_table("bookmarks")
    op.drop_index("idx_user_progress_content", table_name="user_progress")
    op.drop_index("idx_user_progress_user", table_name="user_progress")
    op.drop_table("user_progress")
