"""Add auditable version-pinned report feedback."""

import sqlalchemy as sa
from alembic import op

revision = "20261117_05"
down_revision = "20261117_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "analysis_jobs",
        sa.Column(
            "report_schema_version",
            sa.String(64),
            nullable=False,
            server_default="repwise.evidence-report.v1",
        ),
    )
    op.add_column(
        "analysis_jobs",
        sa.Column(
            "rule_version",
            sa.String(64),
            nullable=False,
            server_default="squat.side.v1",
        ),
    )
    category = sa.Enum(
        "WRONG_COUNT",
        "WRONG_EXERCISE",
        "BAD_TRACKING",
        "MISLEADING_ADVICE",
        name="feedbackcategory",
        native_enum=False,
    )
    op.create_table(
        "report_feedback",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "analysis_id",
            sa.Uuid(),
            sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("category", category, nullable=False),
        sa.Column("rep_index", sa.Integer()),
        sa.Column("check_id", sa.String(128)),
        sa.Column("comment", sa.String(1000)),
        sa.Column("report_schema_version", sa.String(64), nullable=False),
        sa.Column("rule_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_report_feedback_analysis_id", "report_feedback", ["analysis_id"]
    )
    op.create_index("ix_report_feedback_owner_id", "report_feedback", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_report_feedback_owner_id", table_name="report_feedback")
    op.drop_index("ix_report_feedback_analysis_id", table_name="report_feedback")
    op.drop_table("report_feedback")
    op.drop_column("analysis_jobs", "rule_version")
    op.drop_column("analysis_jobs", "report_schema_version")
