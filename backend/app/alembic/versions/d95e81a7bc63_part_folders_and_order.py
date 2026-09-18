"""Store a part's source folder and each feature's card order.

Revision ID: d95e81a7bc63
Revises: c84d70f6ab52
"""

from alembic import op
import sqlalchemy as sa

revision = "d95e81a7bc63"
down_revision = "c84d70f6ab52"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("part", sa.Column("folder_path", sa.String(2048), nullable=True))
    op.add_column(
        "feature",
        sa.Column("part_order", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.alter_column("feature", "part_order", server_default=None)


def downgrade():
    op.drop_column("feature", "part_order")
    op.drop_column("part", "folder_path")
