"""Remember sources the user left without component, so they are not proposed again."""

import sqlalchemy as sa
from alembic import op

revision = "n95c81ebf063"
down_revision = "m84b70daef52"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "part",
        sa.Column(
            "component_unassigned", sa.JSON(), nullable=False, server_default="[]"
        ),
    )


def downgrade():
    op.drop_column("part", "component_unassigned")
