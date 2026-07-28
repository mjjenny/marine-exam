"""add question_as_set to canonical_answers

Stores the verbatim "QUESTION AS SET" exam wording per entry, so the reading page
can show exactly what the examiner asked above the answer.

Revision ID: 0007_canonical_answer_question
Revises: 0006_canonical_answer_title
Create Date: 2026-07-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_canonical_answer_question"
down_revision = "0006_canonical_answer_title"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "canonical_answers", sa.Column("question_as_set", sa.Text(), nullable=True)
    )


def downgrade():
    op.drop_column("canonical_answers", "question_as_set")
