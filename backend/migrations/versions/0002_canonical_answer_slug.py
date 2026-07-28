"""add slug to canonical_answers

Stable reference key for seeding/importing question banks (e.g. EK Electrical),
so re-running a seed updates the same rows rather than duplicating them.

Revision ID: 0002_canonical_answer_slug
Revises: 0001_initial_schema
Create Date: 2026-07-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_canonical_answer_slug"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("canonical_answers", sa.Column("slug", sa.Text(), nullable=True))
    op.create_unique_constraint(
        "uq_canonical_answers_slug", "canonical_answers", ["slug"]
    )


def downgrade():
    op.drop_constraint("uq_canonical_answers_slug", "canonical_answers", type_="unique")
    op.drop_column("canonical_answers", "slug")
