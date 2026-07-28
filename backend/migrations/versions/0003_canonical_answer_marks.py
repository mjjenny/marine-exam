"""add marks to canonical_answers

Nullable: some imported questions have no confirmed mark total (unverified wording).

Revision ID: 0003_canonical_answer_marks
Revises: 0002_canonical_answer_slug
Create Date: 2026-07-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_canonical_answer_marks"
down_revision = "0002_canonical_answer_slug"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("canonical_answers", sa.Column("marks", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("canonical_answers", "marks")
