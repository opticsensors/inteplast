"""Store the material and cavity count entered in the piece editor."""

import sqlalchemy as sa
from alembic import op

revision = "a480e69451bd"
down_revision = "da93b4e81fa2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "material",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
    )
    op.create_index("ix_material_key", "material", ["key"], unique=True)
    op.add_column(
        "part",
        sa.Column(
            "material_id", sa.Uuid(), sa.ForeignKey("material.id", ondelete="RESTRICT")
        ),
    )
    op.create_index("ix_part_material_id", "part", ["material_id"])
    op.add_column("part", sa.Column("cavity_count", sa.Integer()))


def downgrade() -> None:
    op.drop_column("part", "cavity_count")
    op.drop_column("part", "material_id")
    op.drop_table("material")
