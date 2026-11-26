"""Store viewer preferences per account."""

import sqlalchemy as sa
from alembic import op

revision = "c34ed920a518"
down_revision = "b59f1b6372ae"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "cad_projection", sa.String(), nullable=False, server_default="orthographic"
        ),
    )
    op.add_column(
        "user",
        sa.Column(
            "cad_controls", sa.String(), nullable=False, server_default="solidworks"
        ),
    )
    op.add_column(
        "user",
        sa.Column(
            "invert_zoom", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )


def downgrade() -> None:
    op.drop_column("user", "invert_zoom")
    op.drop_column("user", "cad_controls")
    op.drop_column("user", "cad_projection")
