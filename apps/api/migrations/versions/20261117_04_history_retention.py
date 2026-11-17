"""Add analysis history, retention metadata, and deletion tombstones."""

import sqlalchemy as sa
from alembic import op

revision = "20261117_04"
down_revision = "20261117_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analysis_jobs",
        sa.Column("raw_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "analysis_jobs", sa.Column("raw_expired_at", sa.DateTime(timezone=True))
    )
    op.add_column(
        "analysis_jobs", sa.Column("completed_at", sa.DateTime(timezone=True))
    )
    op.add_column("analysis_jobs", sa.Column("deleted_at", sa.DateTime(timezone=True)))
    op.execute(
        "UPDATE analysis_jobs SET raw_expires_at = created_at + INTERVAL '30 days'"
    )
    op.alter_column("analysis_jobs", "raw_expires_at", nullable=False)
    kind = sa.Enum("RAW", "DERIVED", name="artifactkind", native_enum=False)
    op.create_table(
        "analysis_artifacts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "analysis_id",
            sa.Uuid(),
            sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("object_key", sa.String(255), nullable=False, unique=True),
        sa.Column("kind", kind, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_analysis_artifacts_analysis_id", "analysis_artifacts", ["analysis_id"]
    )
    op.create_table(
        "analysis_tombstones",
        sa.Column("analysis_id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_analysis_tombstones_owner_id", "analysis_tombstones", ["owner_id"]
    )
    op.create_table(
        "deletion_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("analysis_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_deletion_requests_owner_id", "deletion_requests", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_deletion_requests_owner_id", table_name="deletion_requests")
    op.drop_table("deletion_requests")
    op.drop_index("ix_analysis_tombstones_owner_id", table_name="analysis_tombstones")
    op.drop_table("analysis_tombstones")
    op.drop_index("ix_analysis_artifacts_analysis_id", table_name="analysis_artifacts")
    op.drop_table("analysis_artifacts")
    op.drop_column("analysis_jobs", "deleted_at")
    op.drop_column("analysis_jobs", "completed_at")
    op.drop_column("analysis_jobs", "raw_expired_at")
    op.drop_column("analysis_jobs", "raw_expires_at")
