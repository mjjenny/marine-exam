"""add per-sitting marks + source to question_instances

Imported question banks (e.g. EK Naval) carry per-sitting mark totals/breakdowns and a
confidence/provenance tag. All nullable — many sittings have only a diet date.

Revision ID: 0005_qi_marks_source
Revises: 0004_subject_is_oral
Create Date: 2026-07-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_qi_marks_source"
down_revision = "0004_subject_is_oral"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("question_instances", sa.Column("total_marks", sa.Integer(), nullable=True))
    op.add_column("question_instances", sa.Column("marks_parts", postgresql.JSONB(), nullable=True))
    op.add_column("question_instances", sa.Column("source", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("question_instances", "source")
    op.drop_column("question_instances", "marks_parts")
    op.drop_column("question_instances", "total_marks")
