"""Add expires_at to users, expand user_status enum with expired + revoked

Revision ID: 0008_user_expires_revoked
Revises: 0007_canonical_answer_question
Create Date: 2026-07-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_user_expires_revoked"
down_revision = "0007_canonical_answer_question"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # Postgres enums cannot be altered inside a transaction; use COMMIT trick.
    bind.execute(sa.text("COMMIT"))
    bind.execute(sa.text("ALTER TYPE user_status ADD VALUE IF NOT EXISTS 'expired'"))
    bind.execute(sa.text("ALTER TYPE user_status ADD VALUE IF NOT EXISTS 'revoked'"))
    bind.execute(sa.text("BEGIN"))

    op.add_column(
        "users",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Back-fill: non-admin approved users get created_at + 365 days.
    bind.execute(sa.text(
        """
        UPDATE users
        SET expires_at = created_at + INTERVAL '365 days'
        WHERE is_admin = false
        """
    ))

    op.create_index("idx_users_expires_at", "users", ["expires_at"])


def downgrade():
    op.drop_index("idx_users_expires_at", table_name="users")
    op.drop_column("users", "expires_at")
    # Postgres does not support removing enum values; downgrade leaves the enum values in place.
