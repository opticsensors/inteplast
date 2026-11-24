"""Optional screenshot of an attachment.

Revision ID: q38fb40ce285
Revises: p27ea3fbd174
"""

import sqlalchemy as sa
from alembic import op

revision = "q38fb40ce285"
down_revision = "p27ea3fbd174"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("storedfile", sa.Column("screenshot_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_storedfile_screenshot",
        "storedfile",
        "storedfile",
        ["screenshot_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_storedfile_screenshot", "storedfile", type_="foreignkey")
    op.drop_column("storedfile", "screenshot_id")
