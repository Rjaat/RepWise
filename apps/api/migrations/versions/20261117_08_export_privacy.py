"""Add export and full account deletion requests."""

import sqlalchemy as sa
from alembic import op

revision = "20261117_08"
down_revision = "20261117_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "export_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("format", sa.String(16), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_export_jobs_owner_id", "export_jobs", ["owner_id"])
    op.create_table(
        "account_deletion_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("account_deletion_requests")
    op.drop_index("ix_export_jobs_owner_id", table_name="export_jobs")
    op.drop_table("export_jobs")
