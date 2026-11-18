"""Piece families and customers as shared lists; features lose tags and category.

The customer text of each piece becomes a `customer` row. Texts that differ only in case or
spaces («Bosch», «bosch», «Bosch ») give one customer, named with the most repeated
spelling or, on a tie, the one of the oldest piece. Nothing else is merged: «Bosch» and
«Robert Bosch» stay two customers.

Feature tags and category are dropped. Going back recreates the columns empty: their
values are only recovered from the database copy taken before migrating.

Revision ID: o16d92fa1c07
Revises: n95c81ebf063
Create Date: 2026-11-17
"""

import uuid
from collections import Counter

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "o16d92fa1c07"
down_revision = "n95c81ebf063"
branch_labels = None
depends_on = None


def spaced(name: str) -> str:
    return " ".join(name.split())


def key(name: str) -> str:
    # Same rule as app.models.catalog_key, frozen here for this migration.
    return spaced(name).casefold()


def create_list(table: str) -> None:
    op.create_table(
        table,
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("key", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f(f"ix_{table}_key"), table, ["key"], unique=True)


def upgrade() -> None:
    create_list("partfamily")
    create_list("customer")
    for column, table in (("family_id", "partfamily"), ("customer_id", "customer")):
        op.add_column("part", sa.Column(column, sa.Uuid(), nullable=True))
        op.create_index(op.f(f"ix_part_{column}"), "part", [column], unique=False)
        op.create_foreign_key(
            f"part_{column}_fkey", "part", table, [column], ["id"], ondelete="RESTRICT"
        )

    db = op.get_bind()
    pieces = db.execute(
        sa.text(
            "SELECT id, customer FROM part "
            "WHERE customer IS NOT NULL AND btrim(customer) <> '' "
            "ORDER BY created_at NULLS LAST, id"
        )
    ).all()
    groups: dict[str, list[tuple[uuid.UUID, str]]] = {}
    for piece_id, text in pieces:
        groups.setdefault(key(text), []).append((piece_id, spaced(text)))
    for group_key, members in groups.items():
        counts = Counter(spelling for _, spelling in members)
        top = max(counts.values())
        # Members are ordered from the oldest piece: the first top spelling wins a tie.
        name = next(spelling for _, spelling in members if counts[spelling] == top)
        customer_id = uuid.uuid4()
        db.execute(
            sa.text("INSERT INTO customer (id, name, key) VALUES (:id, :name, :key)"),
            {"id": customer_id, "name": name, "key": group_key},
        )
        db.execute(
            sa.text("UPDATE part SET customer_id = :customer WHERE id = ANY(:ids)"),
            {"customer": customer_id, "ids": [piece_id for piece_id, _ in members]},
        )
    op.drop_column("part", "customer")

    op.drop_index(op.f("ix_feature_category"), table_name="feature")
    op.drop_column("feature", "category")
    op.drop_column("feature", "tags")


def downgrade() -> None:
    op.add_column(
        "feature",
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column(
        "feature",
        sa.Column("category", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.create_index(op.f("ix_feature_category"), "feature", ["category"], unique=False)

    op.add_column("part", sa.Column("customer", sa.String(255), nullable=True))
    op.execute(
        "UPDATE part SET customer = customer.name FROM customer "
        "WHERE part.customer_id = customer.id"
    )
    for column in ("customer_id", "family_id"):
        op.drop_constraint(f"part_{column}_fkey", "part", type_="foreignkey")
        op.drop_index(op.f(f"ix_part_{column}"), table_name="part")
        op.drop_column("part", column)
    for table in ("customer", "partfamily"):
        op.drop_index(op.f(f"ix_{table}_key"), table_name=table)
        op.drop_table(table)
