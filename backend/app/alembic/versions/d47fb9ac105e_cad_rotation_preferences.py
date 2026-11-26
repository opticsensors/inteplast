"""Store rotation and pivot preferences for each viewer account."""

import sqlalchemy as sa
from alembic import op

revision = "d47fb9ac105e"
down_revision = "c34ed920a518"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "cad_rotation", sa.String(), nullable=False, server_default="arcball"
        ),
    )
    op.add_column(
        "user",
        sa.Column(
            "pick_rotation_center",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("user", "pick_rotation_center")
    op.drop_column("user", "cad_rotation")
