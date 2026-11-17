"""Add durable analysis dispatch state."""

import sqlalchemy as sa
from alembic import op

revision = "20261117_12"
down_revision = "20261117_11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analysis_jobs",
        sa.Column(
            "current_stage",
            sa.String(32),
            nullable=False,
            server_default="dispatch",
        ),
    )
    op.add_column(
        "analysis_jobs", sa.Column("worker_task_id", sa.String(64), nullable=True)
    )
    op.add_column(
        "analysis_jobs", sa.Column("started_at", sa.DateTime(timezone=True))
    )
    op.add_column(
        "analysis_jobs",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_unique_constraint(
        "uq_analysis_jobs_worker_task_id", "analysis_jobs", ["worker_task_id"]
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_analysis_jobs_worker_task_id", "analysis_jobs", type_="unique"
    )
    op.drop_column("analysis_jobs", "updated_at")
    op.drop_column("analysis_jobs", "started_at")
    op.drop_column("analysis_jobs", "worker_task_id")
    op.drop_column("analysis_jobs", "current_stage")
