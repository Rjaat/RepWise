"""Add beta quotas, idempotent usage, and guarded payment attempts."""

import sqlalchemy as sa
from alembic import op

revision = "20261117_11"
down_revision = "20261117_10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "beta_quotas",
        sa.Column("owner_id", sa.Uuid(), primary_key=True),
        sa.Column("limit_units", sa.Integer(), nullable=False),
        sa.Column("used_units", sa.Integer(), nullable=False),
        sa.Column("cycle_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resets_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "usage_ledger",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column(
            "analysis_id",
            sa.Uuid(),
            sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("event_key", sa.String(128), nullable=False, unique=True),
        sa.Column("units", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_usage_ledger_owner_id", "usage_ledger", ["owner_id"])
    op.create_index(
        "ix_usage_ledger_owner_created_at",
        "usage_ledger",
        ["owner_id", "created_at"],
    )
    op.create_table(
        "payment_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "usage_id",
            sa.Uuid(),
            sa.ForeignKey("usage_ledger.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("payment_attempts")
    op.drop_index("ix_usage_ledger_owner_created_at", table_name="usage_ledger")
    op.drop_index("ix_usage_ledger_owner_id", table_name="usage_ledger")
    op.drop_table("usage_ledger")
    op.drop_table("beta_quotas")
