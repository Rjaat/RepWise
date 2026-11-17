"""Add feature flags and audited release promotion history."""

import sqlalchemy as sa
from alembic import op

revision = "20261117_09"
down_revision = "20261117_08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feature_flags",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("check_id", sa.String(128), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("cohort_percent", sa.Integer(), nullable=False),
        sa.Column("active_version", sa.String(64)),
        sa.Column("last_known_good_version", sa.String(64)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "release_promotions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "feature_flag_id",
            sa.Uuid(),
            sa.ForeignKey("feature_flags.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rule_version", sa.String(64), nullable=False),
        sa.Column(
            "approval_id",
            sa.Uuid(),
            sa.ForeignKey("release_approvals.id", ondelete="RESTRICT"),
        ),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("cohort_percent", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_release_promotions_feature_flag_id",
        "release_promotions",
        ["feature_flag_id"],
    )
    op.create_index(
        "ix_release_promotions_actor_id", "release_promotions", ["actor_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_release_promotions_actor_id", table_name="release_promotions")
    op.drop_index(
        "ix_release_promotions_feature_flag_id", table_name="release_promotions"
    )
    op.drop_table("release_promotions")
    op.drop_table("feature_flags")
