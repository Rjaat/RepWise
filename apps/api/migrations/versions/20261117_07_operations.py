"""Add operational metrics, alerts, retries, and support grants."""

import sqlalchemy as sa
from alembic import op

revision = "20261117_07"
down_revision = "20261117_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analysis_jobs",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("analysis_jobs", sa.Column("last_error_category", sa.String(64)))
    op.add_column(
        "analysis_jobs",
        sa.Column(
            "estimated_cost_micros", sa.BigInteger(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "analysis_artifacts",
        sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.create_table(
        "operational_alerts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("message", sa.String(500), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_operational_alerts_analysis_id", "operational_alerts", ["analysis_id"]
    )
    op.create_index(
        "ix_operational_alerts_category", "operational_alerts", ["category"]
    )
    op.create_table(
        "support_access_grants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("support_user_id", sa.Uuid(), nullable=False),
        sa.Column("granted_by", sa.Uuid(), nullable=False),
        sa.Column("case_reference", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_support_access_grants_analysis_id", "support_access_grants", ["analysis_id"]
    )
    op.create_index(
        "ix_support_access_grants_support_user_id",
        "support_access_grants",
        ["support_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_support_access_grants_support_user_id", table_name="support_access_grants"
    )
    op.drop_index(
        "ix_support_access_grants_analysis_id", table_name="support_access_grants"
    )
    op.drop_table("support_access_grants")
    op.drop_index("ix_operational_alerts_category", table_name="operational_alerts")
    op.drop_index("ix_operational_alerts_analysis_id", table_name="operational_alerts")
    op.drop_table("operational_alerts")
    op.drop_column("analysis_artifacts", "size_bytes")
    op.drop_column("analysis_jobs", "estimated_cost_micros")
    op.drop_column("analysis_jobs", "last_error_category")
    op.drop_column("analysis_jobs", "retry_count")
