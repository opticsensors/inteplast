"""Migration p27ea3fbd174 on the isolated test database, with covers in the old shape."""

import json
import uuid

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlmodel import Session

from app.core.db import engine
from app.models import Feature, FeatureAsset, Part

PREVIOUS = "o16d92fa1c07"


def columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(engine).get_columns(table)}


def insert_image(connection: sa.Connection, filename: str) -> uuid.UUID:
    # Build the fixture using the columns present in both historical schemas.
    image_id = uuid.uuid4()
    connection.execute(
        sa.text(
            "INSERT INTO storedfile (id, filename, content_type, size, source)"
            " VALUES (:id, :name, 'image/png', 0, 'upload')"
        ),
        {"id": image_id, "name": filename},
    )
    return image_id


def test_cad_cover_moves_to_its_piece_and_comes_back(db: Session) -> None:
    # Release the shared session so that the schema changes do not wait for it.
    db.commit()
    db.close()
    config = Config("alembic.ini")
    token = uuid.uuid4().hex[:8]
    command.downgrade(config, PREVIOUS)
    try:
        assert "image_id" not in columns("featurepartlink")
        with Session(engine) as session:
            cad_image = insert_image(session.connection(), f"cad-{token}.png")
            pasted = insert_image(session.connection(), f"pasted-{token}.png")
            linked = Part(code=f"L{token}")
            attached = Part(code=f"A{token}")
            session.add_all([linked, attached])
            session.flush()
            cover = {"asset_id": str(uuid.uuid4()), "part_id": str(linked.id)}
            with_cad = Feature(name=f"CAD {token}", image_id=cad_image, cover_3d=cover)
            with_image = Feature(name=f"Image {token}", image_id=pasted)
            session.add_all([with_cad, with_image])
            session.flush()
            # The second piece belongs to the CAD feature only through an attachment.
            session.add(
                FeatureAsset(
                    feature_id=with_cad.id, part_id=attached.id, kind="mold", name="m"
                )
            )
            session.commit()
            ids = {
                "cad_image": cad_image,
                "pasted": pasted,
                "linked": linked.id,
                "attached": attached.id,
                "with_cad": with_cad.id,
                "with_image": with_image.id,
            }
        with engine.begin() as connection:
            for feature in ("with_cad", "with_image"):
                connection.execute(
                    sa.text(
                        "INSERT INTO featurepartlink (feature_id, part_id)"
                        " VALUES (:feature, :part)"
                    ),
                    {"feature": ids[feature], "part": ids["linked"]},
                )

        command.upgrade(config, "head")

        with engine.connect() as connection:
            links = {
                (row.feature_id, row.part_id): row
                for row in connection.execute(
                    sa.text(
                        "SELECT feature_id, part_id, image_id, cover_3d::text AS cover"
                        " FROM featurepartlink WHERE feature_id = ANY(:ids)"
                    ),
                    {"ids": [ids["with_cad"], ids["with_image"]]},
                ).all()
            }
            images = dict(
                connection.execute(
                    sa.text("SELECT id, image_id FROM feature WHERE id = ANY(:ids)"),
                    {"ids": [ids["with_cad"], ids["with_image"]]},
                ).all()
            )
        moved = links[(ids["with_cad"], ids["linked"])]
        assert moved.image_id == ids["cad_image"]
        assert json.loads(moved.cover) == cover
        created = links[(ids["with_cad"], ids["attached"])]
        assert created.image_id is None and created.cover is None
        # The pasted image stays on its feature; its piece has no capture of its own.
        assert links[(ids["with_image"], ids["linked"])].image_id is None
        assert images == {ids["with_cad"]: None, ids["with_image"]: ids["pasted"]}

        command.downgrade(config, PREVIOUS)
        with engine.connect() as connection:
            restored = {
                row.id: row
                for row in connection.execute(
                    sa.text(
                        "SELECT id, image_id, cover_3d::text AS cover FROM feature"
                        " WHERE id = ANY(:ids)"
                    ),
                    {"ids": [ids["with_cad"], ids["with_image"]]},
                ).all()
            }
        assert restored[ids["with_cad"]].image_id == ids["cad_image"]
        assert json.loads(restored[ids["with_cad"]].cover) == cover
        assert restored[ids["with_image"]].image_id == ids["pasted"]
    finally:
        command.upgrade(config, "head")
        with engine.begin() as connection:
            connection.execute(
                sa.text("DELETE FROM feature WHERE name LIKE :like"),
                {"like": f"% {token}"},
            )
            connection.execute(
                sa.text("DELETE FROM part WHERE code LIKE :like"),
                {"like": f"_{token}"},
            )
            connection.execute(
                sa.text("DELETE FROM storedfile WHERE filename LIKE :like"),
                {"like": f"%-{token}.png"},
            )


@pytest.mark.parametrize("change", ["removed", "unlinked", "new photo"])
def test_downgrade_does_not_bring_back_a_removed_cad_cover(
    db: Session, change: str
) -> None:
    """A cover removed, or its piece unlinked, after migrating stays gone going back.

    With a new photo pasted on the feature after unlinking, the photo stays and the old
    faces go: they must not describe another image.
    """
    db.commit()
    db.close()
    config = Config("alembic.ini")
    token = uuid.uuid4().hex[:8]
    command.downgrade(config, PREVIOUS)
    try:
        with Session(engine) as session:
            image_id = insert_image(session.connection(), f"cad-{token}.png")
            part = Part(code=f"L{token}")
            session.add(part)
            session.flush()
            cover = {"asset_id": str(uuid.uuid4()), "part_id": str(part.id)}
            feature = Feature(name=f"CAD {token}", image_id=image_id, cover_3d=cover)
            session.add(feature)
            session.commit()
            feature_id, part_id = feature.id, part.id
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "INSERT INTO featurepartlink (feature_id, part_id)"
                    " VALUES (:feature, :part)"
                ),
                {"feature": feature_id, "part": part_id},
            )

        command.upgrade(config, "head")
        photo_id = None
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "UPDATE featurepartlink SET image_id = NULL, cover_3d = NULL"
                    " WHERE feature_id = :feature"
                    if change == "removed"
                    else "DELETE FROM featurepartlink WHERE feature_id = :feature"
                ),
                {"feature": feature_id},
            )
            if change == "new photo":
                # The feature is left without pieces and gets an image of its own.
                photo_id = insert_image(connection, f"photo-{token}.png")
                connection.execute(
                    sa.text("UPDATE feature SET image_id = :photo WHERE id = :id"),
                    {"photo": photo_id, "id": feature_id},
                )

        command.downgrade(config, PREVIOUS)
        with engine.connect() as connection:
            restored = connection.execute(
                sa.text(
                    "SELECT image_id, cover_3d::text AS cover FROM feature"
                    " WHERE id = :id"
                ),
                {"id": feature_id},
            ).one()
        assert restored.image_id == photo_id
        assert restored.cover is None
    finally:
        command.upgrade(config, "head")
        with engine.begin() as connection:
            connection.execute(
                sa.text("DELETE FROM feature WHERE name = :name"),
                {"name": f"CAD {token}"},
            )
            connection.execute(
                sa.text("DELETE FROM part WHERE code = :code"), {"code": f"L{token}"}
            )
            connection.execute(
                sa.text("DELETE FROM storedfile WHERE filename IN (:cad, :photo)"),
                {"cad": f"cad-{token}.png", "photo": f"photo-{token}.png"},
            )
