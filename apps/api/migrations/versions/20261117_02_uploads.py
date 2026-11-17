"""Create upload and analysis job records."""

import sqlalchemy as sa
from alembic import op

revision = "20261117_02"
down_revision = "20261113_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    upload_status = sa.Enum(
        "INITIATED", "COMPLETED", "CANCELLED", name="uploadstatus", native_enum=False
    )
    op.create_table(
        "media_uploads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("object_key", sa.String(255), nullable=False, unique=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(64), nullable=False),
        sa.Column("declared_size", sa.BigInteger(), nullable=False),
        sa.Column("expected_sha256", sa.String(64), nullable=False),
        sa.Column("status", upload_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("owner_id", "idempotency_key", name="uq_upload_owner_key"),
    )
    op.create_index("ix_media_uploads_owner_id", "media_uploads", ["owner_id"])
    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "upload_id",
            sa.Uuid(),
            sa.ForeignKey("media_uploads.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_analysis_jobs_owner_id", "analysis_jobs", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_analysis_jobs_owner_id", table_name="analysis_jobs")
    op.drop_table("analysis_jobs")
    op.drop_index("ix_media_uploads_owner_id", table_name="media_uploads")
    op.drop_table("media_uploads")
