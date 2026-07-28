"""add title to canonical_answers

So the question title renders even for answers with zero occurrences (empty
question_instances), where no per-sitting question_text exists.

Revision ID: 0006_canonical_answer_title
Revises: 0005_qi_marks_source
Create Date: 2026-07-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_canonical_answer_title"
down_revision = "0005_qi_marks_source"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("canonical_answers", sa.Column("title", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("canonical_answers", "title")
