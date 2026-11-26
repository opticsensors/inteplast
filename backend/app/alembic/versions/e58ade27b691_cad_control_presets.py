"""Fold experimental rotation modes into the two control presets."""

import sqlalchemy as sa
from alembic import op

revision = "e58ade27b691"
down_revision = "d47fb9ac105e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("user", "pick_rotation_center", server_default=sa.true())
    # Adopt the new default for accounts still on the original trial defaults.
    op.execute(
        """UPDATE "user" SET pick_rotation_center = true
           WHERE cad_controls = 'solidworks' AND cad_rotation = 'arcball'
             AND NOT pick_rotation_center AND NOT invert_zoom
             AND cad_projection = 'orthographic'"""
    )
    op.drop_column("user", "cad_rotation")


def downgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "cad_rotation", sa.String(), nullable=False, server_default="arcball"
        ),
    )
    op.execute(
        """UPDATE "user" SET cad_rotation = 'trackball' WHERE cad_controls = 'solidworks'"""
    )
    op.alter_column("user", "pick_rotation_center", server_default=sa.false())
