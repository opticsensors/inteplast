"""Piece identity, multiple named files and last data-read report."""

import sqlalchemy as sa
from alembic import op

revision = "k62f58becd30"
down_revision = "j51e47adbc29"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("part", sa.Column("description", sa.String(2000), nullable=True))
    op.add_column("part", sa.Column("customer", sa.String(255), nullable=True))
    op.add_column(
        "part",
        sa.Column(
            "files_managed", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column("part", sa.Column("last_read", sa.JSON(), nullable=True))
    op.create_table(
        "partfile",
        sa.Column(
            "part_id",
            sa.Uuid(),
            sa.ForeignKey("part.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "file_id",
            sa.Uuid(),
            sa.ForeignKey("storedfile.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("primary", sa.Boolean(), nullable=False),
    )


def downgrade():
    op.drop_table("partfile")
    for column in ("last_read", "files_managed", "customer", "description"):
        op.drop_column("part", column)
