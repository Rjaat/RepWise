"""Add versioned analysis context for safe progress comparisons."""

import sqlalchemy as sa
from alembic import op

revision = "20261117_10"
down_revision = "20261117_09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analysis_jobs",
        sa.Column(
            "exercise", sa.String(64), nullable=False, server_default="bodyweight_squat"
        ),
    )
    op.add_column(
        "analysis_jobs",
        sa.Column(
            "variant", sa.String(64), nullable=False, server_default="bodyweight"
        ),
    )
    op.add_column(
        "analysis_jobs",
        sa.Column("view", sa.String(32), nullable=False, server_default="side"),
    )
    op.add_column(
        "analysis_jobs", sa.Column("assessment_coverage", sa.Float(), nullable=True)
    )
    op.add_column("analysis_jobs", sa.Column("rep_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("analysis_jobs", "rep_count")
    op.drop_column("analysis_jobs", "assessment_coverage")
    op.drop_column("analysis_jobs", "view")
    op.drop_column("analysis_jobs", "variant")
    op.drop_column("analysis_jobs", "exercise")
