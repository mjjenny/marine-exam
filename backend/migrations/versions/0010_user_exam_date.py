"""Add exam_date to users

Revision ID: 0010_user_exam_date
Revises: 0009_user_progress_bookmarks
Create Date: 2026-08-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_user_exam_date"
down_revision = "0009_user_progress_bookmarks"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("exam_date", sa.Date(), nullable=True),
    )


def downgrade():
    op.drop_column("users", "exam_date")
