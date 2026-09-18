import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import AssetKind, NoteKind
from tests.utils.feature import (
    create_random_asset,
    create_random_feature,
    create_random_note,
    create_random_part,
)

BASE = settings.API_V1_STR


@pytest.mark.parametrize("section", ["warning", "lesson", "files", "unassigned"])
def test_content_order_is_atomic_persistent_and_scoped(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
    section: str,
) -> None:
    feature, other_feature = create_random_feature(db), create_random_feature(db)
    if section in ("warning", "lesson"):
        kind = NoteKind(section)
        rows = [create_random_note(db, feature, kind=kind) for _ in range(3)]
        unrelated = create_random_note(
            db,
            feature,
            kind=NoteKind.lesson if kind == NoteKind.warning else NoteKind.warning,
        )
        foreign = create_random_note(db, other_feature, kind=kind)
        scope = {"kind": kind}
        collection, key = "notes", "note_ids"
    else:
        part = create_random_part(db) if section == "files" else None
        rows = [
            create_random_asset(db, feature, part=part, kind=kind)
            for kind in (AssetKind.mold, AssetKind.drawing, AssetKind.part)
        ]
        unrelated = create_random_asset(db, feature, part=create_random_part(db))
        foreign = create_random_asset(db, other_feature, part=part)
        scope = {"part_id": str(part.id) if part else None}
        collection, key = "assets", "asset_ids"
    for index, row in enumerate([*rows, unrelated, foreign]):
        row.position = index + 10
        db.add(row)
    db.commit()
    wanted = [str(row.id) for row in reversed(rows)]
    url = f"{BASE}/features/{feature.id}/{collection}/order"
    response = client.put(
        url, headers=superuser_token_headers, json={**scope, key: wanted}
    )
    assert response.status_code == 200

    def saved_order() -> list[str]:
        saved = client.get(
            f"{BASE}/features/{feature.id}", headers=superuser_token_headers
        ).json()[collection]
        assert (
            next(row for row in saved if row["id"] == str(unrelated.id))["position"]
            == 13
        )
        return [row["id"] for row in saved if row["id"] in wanted]

    assert saved_order() == wanted
    for invalid in (
        wanted[:-1],
        [wanted[0], wanted[0], wanted[2]],
        [wanted[0], wanted[1], str(unrelated.id)],
        [wanted[0], wanted[1], str(foreign.id)],
        [wanted[0], wanted[1], str(uuid.uuid4())],
    ):
        assert (
            client.put(
                url, headers=superuser_token_headers, json={**scope, key: invalid}
            ).status_code
            == 409
        )
        assert saved_order() == wanted
    db.refresh(foreign)
    assert foreign.position == 14
    # Only positions change; content edits and references survive reordering.
    for row in rows:
        original = row.model_dump(exclude={"position"}, warnings=False)
        db.refresh(row)
        assert row.model_dump(exclude={"position"}, warnings=False) == original
