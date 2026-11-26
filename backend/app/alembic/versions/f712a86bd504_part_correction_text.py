"""Keep editable correction text apart from imported measurements."""

import sqlalchemy as sa
from alembic import op

revision = "f712a86bd504"
down_revision = "e58ade27b691"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "partcorrectiontext",
        sa.Column(
            "part_id", sa.Uuid(), sa.ForeignKey("part.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("revision", sa.String(64), nullable=False),
        sa.Column("cota", sa.String(512), nullable=False),
        sa.Column("before", sa.String(64), nullable=False),
        sa.Column("after", sa.String(64), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint(
            "part_id", "revision", "cota", "before", "after", "action"
        ),
    )


def downgrade() -> None:
    op.drop_table("partcorrectiontext")
