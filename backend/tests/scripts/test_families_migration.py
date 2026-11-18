"""Migration o16d92fa1c07 on the isolated test database, with data in the old shape."""

import uuid
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlmodel import Session

from app.core.db import engine

PREVIOUS = "n95c81ebf063"


def columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(engine).get_columns(table)}


def test_customer_texts_become_one_customer_per_normalized_name(db: Session) -> None:
    # Release the shared session so that the schema changes do not wait for it.
    db.commit()
    db.close()
    config = Config("alembic.ini")
    token = uuid.uuid4().hex[:8]
    feature_id = uuid.uuid4()
    command.downgrade(config, PREVIOUS)
    try:
        assert "customer" in columns("part") and "tags" in columns("feature")
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        texts = [
            f"Bosch{token}",
            f"bosch{token}",
            f"Bosch{token} ",
            f"Robert Bosch{token}",
            f"ACME{token}",  # Tie with the newer «Acme»: the oldest piece wins.
            f"Acme{token}",
            "   ",
            None,
        ]
        ids = {}
        with engine.begin() as connection:
            for position, text in enumerate(texts):
                ids[position] = uuid.uuid4()
                connection.execute(
                    sa.text(
                        "INSERT INTO part (id, code, customer, files_managed, components,"
                        " component_unassigned, created_at)"
                        " VALUES (:id, :code, :customer, false, '[]', '[]', :created)"
                    ),
                    {
                        "id": ids[position],
                        "code": f"M{token}{position}",
                        "customer": text,
                        "created": start + timedelta(days=position),
                    },
                )
            connection.execute(
                sa.text(
                    "INSERT INTO feature (id, name, category, tags, part_order)"
                    " VALUES (:id, :name, 'hole', ARRAY['bomba','automoción'], '[]')"
                ),
                {"id": feature_id, "name": f"Bolt Eye {token}"},
            )
        command.upgrade(config, "head")

        assert "customer" not in columns("part")
        assert not {"tags", "category"} & columns("feature")
        with engine.connect() as connection:
            rows = connection.execute(
                sa.text(
                    "SELECT part.id, customer.name FROM part"
                    " LEFT JOIN customer ON customer.id = part.customer_id"
                    " WHERE part.id = ANY(:ids)"
                ),
                {"ids": list(ids.values())},
            ).all()
            names = dict(rows)
            customers = (
                connection.execute(
                    sa.text("SELECT name FROM customer WHERE name LIKE :like"),
                    {"like": f"%{token}%"},
                )
                .scalars()
                .all()
            )
            feature = connection.execute(
                sa.text("SELECT name FROM feature WHERE id = :id"), {"id": feature_id}
            ).scalar_one()
        bosch, acme = f"Bosch{token}", f"ACME{token}"
        assert [names[ids[i]] for i in range(8)] == [
            bosch,
            bosch,
            bosch,
            f"Robert {bosch}",
            acme,
            acme,
            None,
            None,
        ]
        assert sorted(customers) == sorted([bosch, f"Robert {bosch}", acme])
        assert feature == f"Bolt Eye {token}"

        # Going back restores the customer text; tags and category come back empty.
        command.downgrade(config, PREVIOUS)
        with engine.connect() as connection:
            restored = dict(
                connection.execute(
                    sa.text("SELECT id, customer FROM part WHERE id = ANY(:ids)"),
                    {"ids": list(ids.values())},
                ).all()
            )
            tags, category = connection.execute(
                sa.text("SELECT tags, category FROM feature WHERE id = :id"),
                {"id": feature_id},
            ).one()
        assert restored[ids[1]] == bosch and restored[ids[5]] == acme
        assert restored[ids[6]] is None
        assert tags == [] and category is None
    finally:
        command.upgrade(config, "head")
        with engine.begin() as connection:
            connection.execute(
                sa.text("DELETE FROM part WHERE code LIKE :like"),
                {"like": f"M{token}%"},
            )
            connection.execute(
                sa.text("DELETE FROM feature WHERE id = :id"), {"id": feature_id}
            )
            connection.execute(
                sa.text(
                    "DELETE FROM customer WHERE name LIKE :like"
                    " AND id NOT IN (SELECT customer_id FROM part"
                    " WHERE customer_id IS NOT NULL)"
                ),
                {"like": f"%{token}%"},
            )
