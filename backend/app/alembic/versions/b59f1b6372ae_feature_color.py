"""Assign a persistent palette position to each feature."""

import sqlalchemy as sa
from alembic import op

revision = "b59f1b6372ae"
down_revision = "a480e69451bd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE feature_color_seq")
    op.add_column("feature", sa.Column("color_slot", sa.Integer()))
    op.execute("""
        UPDATE feature SET color_slot = ranked.slot
        FROM (SELECT id, row_number() OVER (ORDER BY lower(name), id) AS slot FROM feature) ranked
        WHERE feature.id = ranked.id
    """)
    op.execute(
        "SELECT setval('feature_color_seq', COALESCE(max(color_slot), 0) + 1, false) FROM feature"
    )
    op.alter_column(
        "feature",
        "color_slot",
        nullable=False,
        server_default=sa.text("nextval('feature_color_seq')"),
    )
    op.execute("ALTER SEQUENCE feature_color_seq OWNED BY feature.color_slot")


def downgrade() -> None:
    op.drop_column("feature", "color_slot")
