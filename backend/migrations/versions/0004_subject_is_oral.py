"""add is_oral flag to subjects

Marks EK Oral as the flat topic/search subject (no diet layer). Explicit flag so
diet-based subjects with no content yet still present correctly.

Revision ID: 0004_subject_is_oral
Revises: 0003_canonical_answer_marks
Create Date: 2026-07-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_subject_is_oral"
down_revision = "0003_canonical_answer_marks"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "subjects",
        sa.Column("is_oral", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.execute("UPDATE subjects SET is_oral = true WHERE slug = 'ek-oral'")


def downgrade():
    op.drop_column("subjects", "is_oral")
