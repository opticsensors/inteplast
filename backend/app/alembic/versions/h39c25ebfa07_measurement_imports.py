"""Keep source measurements and their import history per piece.

Revision ID: h39c25ebfa07
Revises: g28b14daef96
"""

import sqlalchemy as sa
from alembic import op

revision = "h39c25ebfa07"
down_revision = "g28b14daef96"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "measurementimport",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "part_id",
            sa.Uuid(),
            sa.ForeignKey("part.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("revision", sa.String(64), nullable=False),
        sa.Column("sample", sa.String(64), nullable=False),
        sa.Column("cavity", sa.String(64), nullable=False),
        sa.Column("source_path", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("reader", sa.String(64), nullable=False),
        sa.Column("rows", sa.JSON(), nullable=False),
        sa.Column("baseline", sa.JSON()),
        sa.Column(
            "imported_by", sa.Uuid(), sa.ForeignKey("user.id", ondelete="SET NULL")
        ),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_measurementimport_part_id", "measurementimport", ["part_id"])
    op.create_index("ix_measurementimport_revision", "measurementimport", ["revision"])


def downgrade():
    op.drop_table("measurementimport")
