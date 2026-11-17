"""Add verified user accounts and revocable sessions."""

import sqlalchemy as sa
from alembic import op

revision = "20261117_03"
down_revision = "20261117_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    role = sa.Enum(
        "USER", "REVIEWER", "ADMIN", "SUPPORT", name="userrole", native_enum=False
    )
    op.create_table(
        "user_accounts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("external_subject", sa.String(255), nullable=False, unique=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("email_verified", sa.Boolean(), nullable=False),
        sa.Column("role", role, nullable=False),
        sa.Column("disabled_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("user_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("refresh_token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column(
            "rotated_from_id",
            sa.Uuid(),
            sa.ForeignKey("auth_sessions.id", ondelete="SET NULL"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_table("user_accounts")
