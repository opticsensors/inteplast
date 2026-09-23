"""Remember explicit piece references, including removed legacy links."""

import sqlalchemy as sa
from alembic import op

revision = "j51e47adbc29"
down_revision = "i40d36fcab18"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "partreference",
        sa.Column(
            "part_id",
            sa.Uuid(),
            sa.ForeignKey("part.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("kind", sa.String(16), primary_key=True),
        sa.Column(
            "file_id",
            sa.Uuid(),
            sa.ForeignKey("storedfile.id", ondelete="RESTRICT"),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_table("partreference")
