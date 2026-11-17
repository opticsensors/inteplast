"""Keep characteristic numbers separate by component; preserve existing default identities."""

from alembic import op
import sqlalchemy as sa

revision = "m84b70daef52"
down_revision = "l73a69cfde41"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "part", sa.Column("components", sa.JSON(), nullable=False, server_default="[]")
    )
    op.add_column(
        "partcharacteristic",
        sa.Column("component", sa.String(24), nullable=False, server_default=""),
    )
    # The initial constraint was unnamed: inspect instead of assuming PostgreSQL's name.
    for constraint in sa.inspect(op.get_bind()).get_unique_constraints(
        "partcharacteristic"
    ):
        if set(constraint["column_names"]) == {"part_id", "code", "revision"}:
            op.drop_constraint(constraint["name"], "partcharacteristic", type_="unique")
    op.create_unique_constraint(
        "uq_characteristic_component",
        "partcharacteristic",
        ["part_id", "component", "code", "revision"],
    )


def downgrade():
    # Refuse a downgrade that would collapse two real identities.
    duplicates = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT 1 FROM partcharacteristic GROUP BY part_id, code, revision HAVING count(*) > 1 LIMIT 1"
            )
        )
        .first()
    )
    if duplicates:
        raise RuntimeError(
            "Existen cotas de distintos componentes; no se pueden fusionar al revertir."
        )
    op.drop_constraint(
        "uq_characteristic_component", "partcharacteristic", type_="unique"
    )
    op.create_unique_constraint(
        "uq_characteristic_legacy",
        "partcharacteristic",
        ["part_id", "code", "revision"],
    )
    op.drop_column("partcharacteristic", "component")
    op.drop_column("part", "components")
