"""Add consented annotation review and release audit records."""

import sqlalchemy as sa
from alembic import op

revision = "20261117_06"
down_revision = "20261117_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_consents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "analysis_id",
            sa.Uuid(),
            sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(255), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_research_consents_owner_id", "research_consents", ["owner_id"])
    op.create_table(
        "annotation_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "analysis_id",
            sa.Uuid(),
            sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "consent_id",
            sa.Uuid(),
            sa.ForeignKey("research_consents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reviewer_id",
            sa.Uuid(),
            sa.ForeignKey("user_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("assigned_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_annotation_assignments_analysis_id",
        "annotation_assignments",
        ["analysis_id"],
    )
    op.create_index(
        "ix_annotation_assignments_reviewer_id",
        "annotation_assignments",
        ["reviewer_id"],
    )
    op.create_table(
        "annotations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "assignment_id",
            sa.Uuid(),
            sa.ForeignKey("annotation_assignments.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.Column("labels", sa.JSON(), nullable=False),
        sa.Column("uncertain", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_annotations_reviewer_id", "annotations", ["reviewer_id"])
    op.create_table(
        "adjudications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "assignment_id",
            sa.Uuid(),
            sa.ForeignKey("annotation_assignments.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("adjudicator_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_adjudications_adjudicator_id", "adjudications", ["adjudicator_id"]
    )
    op.create_table(
        "release_approvals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("rule_version", sa.String(64), nullable=False),
        sa.Column(
            "adjudication_id",
            sa.Uuid(),
            sa.ForeignKey("adjudications.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("approver_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_release_approvals_rule_version", "release_approvals", ["rule_version"]
    )
    op.create_index(
        "ix_release_approvals_approver_id", "release_approvals", ["approver_id"]
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])


def downgrade() -> None:
    for table, indexes in (
        ("audit_events", ("ix_audit_events_action", "ix_audit_events_actor_id")),
        (
            "release_approvals",
            ("ix_release_approvals_approver_id", "ix_release_approvals_rule_version"),
        ),
        ("adjudications", ("ix_adjudications_adjudicator_id",)),
        ("annotations", ("ix_annotations_reviewer_id",)),
        (
            "annotation_assignments",
            (
                "ix_annotation_assignments_reviewer_id",
                "ix_annotation_assignments_analysis_id",
            ),
        ),
        ("research_consents", ("ix_research_consents_owner_id",)),
    ):
        for index in indexes:
            op.drop_index(index, table_name=table)
        op.drop_table(table)
