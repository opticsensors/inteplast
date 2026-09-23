"""Add a rebuildable vector cache owned by the assistant module."""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "i40d36fcab18"
down_revision = "h39c25ebfa07"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "assistant_embedding",
        sa.Column("id", sa.String(512), primary_key=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("embedding", Vector(), nullable=False),
    )


def downgrade():
    op.drop_table("assistant_embedding")
    # The extension may also be used by other modules; leave it installed.
