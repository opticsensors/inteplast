"""Persist the selected originals folder without replacing deployment defaults."""

import sqlalchemy as sa
from alembic import op

revision = "da93b4e81fa2"
down_revision = "q38fb40ce285"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sharepointfolder",
        sa.Column("source_id", sa.String(100), primary_key=True),
        sa.Column("drive_id", sa.String(), nullable=False),
        sa.Column("item_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("web_url", sa.String(), nullable=False),
        sa.Column("revision", sa.Uuid(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("sharepointfolder")
