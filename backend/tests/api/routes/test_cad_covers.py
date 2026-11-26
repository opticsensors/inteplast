import hashlib
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Any

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import feature_covers
from app.api.routes import features
from app.core.config import settings
from app.models import AssetKind, Feature, FeaturePartLink, Part, StoredFile
from tests.utils.feature import (
    create_random_asset,
    create_random_feature,
    create_random_part,
)

API = settings.API_V1_STR


def upload(
    client: TestClient, headers: dict[str, str], name: str, raw: bytes, kind: str
) -> dict[str, Any]:
    return client.post(
        f"{API}/files/", headers=headers, files={"file": (name, raw, kind)}
    ).json()


def cover_example(
    client: TestClient, headers: dict[str, str], db: Session
) -> tuple[str, str, dict[str, Any]]:
    """A feature with one piece whose STEP is attached, and a cover body for it."""
    feature = create_random_feature(db)
    part = create_random_part(db)
    raw = b"ISO-10303-21; test source bytes; END-ISO-10303-21;"
    file = upload(client, headers, "piece.stp", raw, "application/octet-stream")
    image = upload(client, headers, "cover.png", b"image fixture", "image/png")
    asset = create_random_asset(db, feature, kind=AssetKind.part, part=part)
    asset.file_id = uuid.UUID(file["id"])
    db.add(asset)
    db.commit()
    return (
        str(feature.id),
        str(part.id),
        {
            "image_id": image["id"],
            "cover_3d": {
                "asset_id": str(asset.id),
                "part_id": str(part.id),
                "file_id": file["id"],
                "file_version": file["version"],
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "geometry_key": "a" * 64,
                "recipe": "occt-import-js@0.0.23/cover-v1",
                "faces": [{"mesh": 0, "face": 3}, {"mesh": 0, "face": 8}],
                "camera": {
                    "position": [20, -20, 20],
                    "target": [0, 0, 0],
                    "up": [0, 0, 1],
                },
            },
        },
    )


def save(
    client: TestClient,
    headers: dict[str, str],
    feature_id: str,
    covers: list[dict[str, Any]],
    **header: Any,
) -> Any:
    """The page's «Guardar»: header and changed covers in one request."""
    return client.put(
        f"{API}/features/{feature_id}",
        headers=headers,
        json={**header, "part_covers": covers},
    )


def detail(client: TestClient, headers: dict[str, str], feature_id: str) -> Any:
    return client.get(f"{API}/features/{feature_id}", headers=headers).json()


def cover_of(feature: dict[str, Any], part_id: str) -> dict[str, Any]:
    return next(c for c in feature["part_covers"] if c["part_id"] == part_id)


def link(
    client: TestClient, headers: dict[str, str], feature_id: str, part: Any
) -> None:
    result = client.post(
        f"{API}/features/{feature_id}/parts/{part.id}", headers=headers
    )
    assert result.status_code == 200, result.text


def test_attachment_creates_the_piece_link(db: Session) -> None:
    feature = create_random_feature(db)
    part = create_random_part(db)
    create_random_asset(db, feature, kind=AssetKind.part, part=part)
    assert db.get(FeaturePartLink, (feature.id, part.id)) is not None


def test_colored_capture_is_versioned_separately_from_the_original_and_gray(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    headers = superuser_token_headers
    feature, part, body = cover_example(client, headers, db)
    url = f"{API}/parts/{part}/cover"
    selection = body["cover_3d"]
    assert (
        save(client, headers, feature, [{"part_id": part, **body}]).status_code == 200
    )
    first = client.get(url, headers=headers).json()
    colors = first["face_colors"]
    assert colors["review"] == {}
    assert [
        (layer["feature_id"], layer["selection"]) for layer in colors["layers"]
    ] == [(feature, selection)]
    assert detail(client, headers, feature)["marked_part_ids"] == [part]
    # Simulate a persisted annotation from before colour support.
    link = db.get(FeaturePartLink, (uuid.UUID(feature), uuid.UUID(part)))
    assert link and link.cover_3d
    link.cover_3d = {
        key: value
        for key, value in link.cover_3d.items()
        if key not in {"source_key", "primary_at_selection"}
    }
    db.add(link)
    db.commit()
    png = upload(
        client, headers, "colores.png", b"different derived image", "image/png"
    )
    request = {
        **{
            k: selection[k]
            for k in ("file_id", "file_version", "source_sha256", "geometry_key")
        },
        "render_key": colors["key"],
        "image_id": png["id"],
    }
    for variant in (None, feature):
        response = client.put(
            f"{API}/parts/{part}/face-image",
            headers=headers,
            json={**request, "feature_id": variant},
        )
        assert response.status_code == 200, response.text
    colored = client.get(url, headers=headers).json()
    assert set(colored["face_colors"]["images"]) == {"part", feature}
    assert colored["image"] == first["image"]
    graph = client.get(
        f"{API}/catalog/graph",
        headers=headers,
        params={"part_id": part, "kind": "part"},
    ).json()
    piece_node = next(node for node in graph["nodes"] if node["kind"] == "part")
    assert piece_node["image"]["id"] == png["id"]
    assert detail(client, headers, feature)["cover_image"]["id"] == body["image_id"]
    db.refresh(link)
    assert link.cover_3d and link.cover_3d["source_key"]
    updated = {**selection, "faces": [{"mesh": 0, "face": 4}]}
    assert (
        save(
            client, headers, feature, [{"part_id": part, **body, "cover_3d": updated}]
        ).status_code
        == 200
    )
    assert (
        client.put(
            f"{API}/parts/{part}/face-image", headers=headers, json=request
        ).status_code
        == 409
    )
    assert client.get(url, headers=headers).json()["face_colors"]["images"] == {}
    cleared = save(
        client, headers, feature, [{"part_id": part, "image_id": body["image_id"]}]
    )
    assert cleared.status_code == 200
    assert cleared.json()["marked_part_ids"] == []
    assert client.get(url, headers=headers).json()["face_colors"] is None


def test_perspective_thumbnails_survive_the_viewer_upgrade(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    from app.evidence import digest, job_id
    from app.knowledge_models import EvidenceJob

    headers = superuser_token_headers
    feature, part, body = cover_example(client, headers, db)
    url = f"{API}/parts/{part}"
    assert (
        save(client, headers, feature, [{"part_id": part, **body}]).status_code == 200
    )
    cover = client.get(f"{url}/cover", headers=headers).json()
    selection = body["cover_3d"]
    payload = {k: selection[k] for k in ("file_id", "file_version", "source_sha256")}
    payload["image_id"] = body["image_id"]
    assert (
        client.put(
            f"{url}/cover",
            headers=headers,
            json={**payload, "cad_cache_key": cover["cad_cache_key"]},
        ).status_code
        == 200
    )
    assert (
        client.put(
            f"{url}/face-image",
            headers=headers,
            json={
                **payload,
                "render_key": cover["face_colors"]["key"],
                "geometry_key": selection["geometry_key"],
            },
        ).status_code
        == 200
    )

    gray = db.get(EvidenceJob, job_id("part-cover", uuid.UUID(part)))
    colors = db.get(EvidenceJob, job_id("face-colors", uuid.UUID(part)))
    assert gray and colors
    source = gray.payload["source_key"]
    gray.cache_key = hashlib.sha256(f"shaded-edges-v1:{source}".encode()).hexdigest()
    layer = cover["face_colors"]["layers"][0]
    colors.cache_key = digest(
        ["face-colors-v2", source, [[feature, layer["color"], layer["selection"]]]]
    )
    db.add_all([gray, colors])
    db.commit()
    restored = client.get(f"{url}/cover", headers=headers).json()
    assert restored["image"]["id"] == body["image_id"]
    assert restored["cover_needs_refresh"] is False
    assert restored["face_colors"]["images"]["part"]["id"] == body["image_id"]
    assert (
        client.put(
            f"{url}/face-image",
            headers=headers,
            json={
                **payload,
                "render_key": restored["face_colors"]["key"],
                "feature_id": feature,
                "geometry_key": selection["geometry_key"],
            },
        ).status_code
        == 200
    )
    assert set(
        client.get(f"{url}/cover", headers=headers).json()["face_colors"]["images"]
    ) == {"part", feature}


def test_face_review_follows_the_marked_piece_even_when_it_is_not_first(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    from app.file_sources import document_path

    headers = superuser_token_headers
    feature, part, body = cover_example(client, headers, db)
    first = create_random_part(db)
    link(client, headers, feature, first)
    assert (
        save(client, headers, feature, [{"part_id": part, **body}]).status_code == 200
    )
    order = client.put(
        f"{API}/features/{feature}/parts/order",
        headers=headers,
        json={"part_ids": [str(first.id), part]},
    )
    assert order.status_code == 200, order.text
    card = detail(client, headers, feature)
    assert card["marked_part_ids"] == [part] and card["first_marked_part_id"] is None
    doc = db.get(StoredFile, uuid.UUID(body["cover_3d"]["file_id"]))
    assert doc
    document_path(doc).write_bytes(b"changed STEP in the test upload directory")
    colors = client.get(f"{API}/parts/{part}/cover", headers=headers).json()[
        "face_colors"
    ]
    assert colors["review"] == {feature: card["name"]} and colors["layers"] == []
    assert (
        client.get(f"{API}/parts/{first.id}/cover", headers=headers).json()[
            "face_colors"
        ]
        is None
    )
    assert (
        cover_of(detail(client, headers, feature), part)["image"]["id"]
        == body["image_id"]
    )


@pytest.mark.parametrize(
    "attach_first", [True, False], ids=["attach-first", "unlink-first"]
)
def test_adding_attachment_and_unlinking_piece_concurrently(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    attach_first: bool,
) -> None:
    headers = superuser_token_headers
    feature_id, part_id, body = cover_example(client, headers, db)
    saved = save(client, headers, feature_id, [{"part_id": part_id, **body}])
    assert saved.status_code == 200, saved.text
    url = f"{API}/features/{feature_id}"

    def attach() -> int:
        return client.post(
            f"{url}/assets",
            headers=headers,
            json={
                "part_id": part_id,
                "kind": "part",
                "name": "piece.stp",
                "file_id": body["cover_3d"]["file_id"],
            },
        ).status_code

    def unlink() -> int:
        return client.delete(f"{url}/parts/{part_id}", headers=headers).status_code

    first_locked, second_entered, release = (threading.Event() for _ in range(3))
    lock = features.lock_feature

    def ordered_lock(session: Session, feature_id: uuid.UUID) -> Feature:
        if first_locked.is_set():
            second_entered.set()
            return lock(session, feature_id)
        feature = lock(session, feature_id)
        first_locked.set()
        assert release.wait(10)
        return feature

    first, second = (attach, unlink) if attach_first else (unlink, attach)
    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as workers:
        patch.setattr(features, "lock_feature", ordered_lock)
        first_request = workers.submit(first)
        try:
            assert first_locked.wait(10)
            second_request = workers.submit(second)
            assert second_entered.wait(10)
            with pytest.raises(FutureTimeout):
                second_request.result(timeout=0.25)
        finally:
            release.set()
        assert first_request.result(timeout=10) == 200
        assert second_request.result(timeout=10) == 200

    feature = detail(client, headers, feature_id)
    remaining = [] if attach_first else [part_id]
    assert [part["id"] for part in feature["parts"]] == remaining
    assert [asset["part"]["id"] for asset in feature["assets"]] == remaining
    assert [cover["part_id"] for cover in feature["part_covers"]] == remaining
    if remaining:
        assert cover_of(feature, part_id)["image"] is None
        assert cover_of(feature, part_id)["cover_3d"] is None
    result = save(
        client,
        headers,
        feature_id,
        [{"part_id": part_id, "image_id": body["image_id"]}],
    )
    assert result.status_code == (409 if attach_first else 200)


def test_cover_persists_per_piece_and_can_be_removed(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    headers = superuser_token_headers
    feature_id, part_id, body = cover_example(client, headers, db)
    body["cover_3d"]["camera"]["ortho_height"] = 14.75
    change = {"part_id": part_id, **body}
    assert save(client, {}, feature_id, [change]).status_code == 401
    result = save(client, headers, feature_id, [change])
    assert result.status_code == 200, result.text

    # An unrelated edit of the feature keeps the cover of the piece.
    client.put(
        f"{API}/features/{feature_id}",
        headers=headers,
        json={"description": "New description"},
    )
    feature = detail(client, headers, feature_id)
    assert [cover["part_id"] for cover in feature["part_covers"]] == [part_id]
    assert feature["part_covers"][0]["cover_3d"] == body["cover_3d"]
    assert feature["part_covers"][0]["image"]["id"] == body["image_id"]
    assert feature["cover_image"]["id"] == body["image_id"]
    assert feature["part_count"] == 1
    assert "cover_3d" not in feature
    assert feature["image"] is None

    # No image: back to the piece's CAD capture (none here).
    result = save(client, headers, feature_id, [{"part_id": part_id}])
    assert result.status_code == 200, result.text
    feature = detail(client, headers, feature_id)
    assert feature["part_covers"][0]["image"] is None
    assert feature["part_covers"][0]["cover_3d"] is None
    assert feature["cover_image"] is None


def test_image_cover_without_cad(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    headers = superuser_token_headers
    feature_id, part_id, body = cover_example(client, headers, db)
    result = save(
        client,
        headers,
        feature_id,
        [{"part_id": part_id, "image_id": body["image_id"]}],
    )
    assert result.status_code == 200, result.text
    assert cover_of(detail(client, headers, feature_id), part_id)["cover_3d"] is None
    document = upload(client, headers, "notes.pdf", b"%PDF-1.4", "application/pdf")
    result = save(
        client, headers, feature_id, [{"part_id": part_id, "image_id": document["id"]}]
    )
    assert result.status_code == 422


def test_header_and_covers_are_saved_together_or_not_at_all(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """The second cover fails: neither the title nor the first cover change."""
    headers = superuser_token_headers
    feature_id, part_id, body = cover_example(client, headers, db)
    second = create_random_part(db)
    link(client, headers, feature_id, second)
    before = detail(client, headers, feature_id)
    good = upload(client, headers, "first.png", b"first", "image/png")
    document = upload(client, headers, "notes.pdf", b"%PDF-1.4", "application/pdf")
    result = save(
        client,
        headers,
        feature_id,
        [
            {"part_id": part_id, "image_id": good["id"]},
            {"part_id": str(second.id), "image_id": document["id"]},
        ],
        name="Must not save",
    )
    assert result.status_code == 422
    db.expire_all()
    after = detail(client, headers, feature_id)
    assert after["name"] == before["name"]
    assert after["part_covers"] == before["part_covers"]
    assert (
        db.get(FeaturePartLink, (uuid.UUID(feature_id), uuid.UUID(part_id))).image_id
        is None
    )  # type: ignore[union-attr]

    # A changed STEP on the second piece also stops the whole save.
    source = settings.uploads_path / body["cover_3d"]["file_id"]
    source.write_bytes(b"new revision")
    result = save(
        client,
        headers,
        feature_id,
        [
            {"part_id": str(second.id), "image_id": good["id"]},
            {"part_id": part_id, **body},
        ],
        name="Must not save either",
    )
    assert result.status_code == 409
    after = detail(client, headers, feature_id)
    assert after["name"] == before["name"]
    assert after["part_covers"] == before["part_covers"]


def test_a_piece_removed_meanwhile_is_a_conflict(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    headers = superuser_token_headers
    feature_id, part_id, body = cover_example(client, headers, db)
    other = create_random_part(db)
    link(client, headers, feature_id, other)
    # Someone else unlinks the other piece while this page edits its cover.
    client.delete(f"{API}/features/{feature_id}/parts/{other.id}", headers=headers)
    result = save(
        client,
        headers,
        feature_id,
        [
            {"part_id": part_id, **body},
            {"part_id": str(other.id), "image_id": body["image_id"]},
        ],
        name="Retry later",
    )
    assert result.status_code == 409
    assert other.code in result.json()["detail"]
    feature = detail(client, headers, feature_id)
    assert feature["name"] != "Retry later"
    assert cover_of(feature, part_id)["image"] is None
    # The retry without that piece keeps the other changes.
    result = save(
        client, headers, feature_id, [{"part_id": part_id, **body}], name="Retry later"
    )
    assert result.status_code == 200, result.text
    feature = detail(client, headers, feature_id)
    assert feature["name"] == "Retry later"
    assert cover_of(feature, part_id)["cover_3d"] == body["cover_3d"]


def test_cover_rejects_cad_of_another_piece_or_feature(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    headers = superuser_token_headers
    feature_id, part_id, body = cover_example(client, headers, db)
    # A piece that is not in the feature has no cover there.
    stranger = create_random_part(db)
    result = save(client, headers, feature_id, [{**body, "part_id": str(stranger.id)}])
    assert result.status_code == 409
    # A second piece of the same feature cannot take the first one's selection.
    other = create_random_part(db)
    link(client, headers, feature_id, other)
    result = save(client, headers, feature_id, [{**body, "part_id": str(other.id)}])
    assert result.status_code == 409
    # Another feature on the same piece cannot use this feature's attachment.
    feature = create_random_feature(db)
    link(client, headers, str(feature.id), db.get(Part, uuid.UUID(part_id)))
    result = save(client, headers, str(feature.id), [{"part_id": part_id, **body}])
    assert result.status_code == 409
    # The same piece twice in one save.
    result = save(
        client,
        headers,
        feature_id,
        [{"part_id": part_id, **body}, {"part_id": part_id}],
    )
    assert result.status_code == 422


def test_cover_requires_valid_selection_and_camera(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    headers = superuser_token_headers
    feature_id, part_id, body = cover_example(client, headers, db)
    annotation = body["cover_3d"]
    for changes in [
        {"faces": []},
        {"faces": [{"mesh": -1, "face": 0}]},
        {"faces": [{"mesh": 0, "face": 1}] * 2},
        {"camera": {"position": [0, 0, 0], "target": [0, 0, 0], "up": [0, 0, 1]}},
        {"camera": {**annotation["camera"], "ortho_height": 0}},
        {"recipe": "unknown renderer"},
    ]:
        result = save(
            client,
            headers,
            feature_id,
            [{**body, "part_id": part_id, "cover_3d": {**annotation, **changes}}],
        )
        assert result.status_code == 422, result.text
    # A selection without its image.
    result = save(
        client, headers, feature_id, [{"part_id": part_id, "cover_3d": annotation}]
    )
    assert result.status_code == 422


def test_whole_component_cover_reopens_on_the_chosen_step(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    headers = superuser_token_headers
    feature_id, part_id, body = cover_example(client, headers, db)
    second = upload(client, headers, "lid.stp", b"second STEP", "model/step")
    asset = client.post(
        f"{API}/features/{feature_id}/assets",
        headers=headers,
        json={
            "part_id": part_id,
            "kind": "part",
            "file_id": second["id"],
            "name": "Lid",
        },
    )
    assert asset.status_code == 200
    body["cover_3d"].update(
        asset_id=asset.json()["id"],
        file_id=second["id"],
        file_version=second["version"],
        source_sha256=hashlib.sha256(b"second STEP").hexdigest(),
        faces=[],
    )
    result = save(client, headers, feature_id, [{"part_id": part_id, **body}])
    assert result.status_code == 200, result.text
    saved = cover_of(detail(client, headers, feature_id), part_id)["cover_3d"]
    assert saved["asset_id"] == asset.json()["id"] and saved["faces"] == []


def test_a_page_from_before_covers_per_piece_is_rejected(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """An open tab of the old version sends `cover_3d` on the feature: never ignored."""
    headers = superuser_token_headers
    feature_id, part_id, body = cover_example(client, headers, db)
    before = detail(client, headers, feature_id)
    result = client.put(
        f"{API}/features/{feature_id}",
        headers=headers,
        json={"name": "Old tab", **body},
    )
    assert result.status_code == 422
    assert "part_covers" in result.text
    after = detail(client, headers, feature_id)
    assert after["name"] == before["name"]
    assert cover_of(after, part_id)["image"] is None


def test_unlinking_a_piece_keeps_the_other_covers_and_the_file(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    headers = superuser_token_headers
    feature_id, part_id, body = cover_example(client, headers, db)
    other = create_random_part(db)
    link(client, headers, feature_id, other)
    image = upload(client, headers, "b.png", b"other", "image/png")
    result = save(
        client,
        headers,
        feature_id,
        [
            {"part_id": part_id, **body},
            {"part_id": str(other.id), "image_id": image["id"]},
        ],
    )
    assert result.status_code == 200, result.text

    result = client.delete(
        f"{API}/features/{feature_id}/parts/{other.id}", headers=headers
    )
    assert result.status_code == 200
    feature = detail(client, headers, feature_id)
    assert [cover["part_id"] for cover in feature["part_covers"]] == [part_id]
    assert feature["part_covers"][0]["cover_3d"] == body["cover_3d"]
    assert feature["part_count"] == 1
    # The uploaded image is kept; only the link to it goes.
    assert db.get(StoredFile, uuid.UUID(image["id"])) is not None

    # Linking the piece again starts without its old cover.
    link(client, headers, feature_id, other)
    again = cover_of(detail(client, headers, feature_id), str(other.id))
    assert again["image"] is None


def test_removing_the_step_keeps_the_image(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    headers = superuser_token_headers
    feature_id, part_id, body = cover_example(client, headers, db)
    save(client, headers, feature_id, [{"part_id": part_id, **body}])
    result = client.delete(
        f"{API}/features/assets/{body['cover_3d']['asset_id']}", headers=headers
    )
    assert result.status_code == 200
    cover = cover_of(detail(client, headers, feature_id), part_id)
    assert cover["image"]["id"] == body["image_id"]
    assert cover["cover_3d"] is None


def test_card_and_page_use_one_order_and_count_pieces(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    headers = superuser_token_headers
    feature = create_random_feature(db)
    own = upload(client, headers, "f.png", b"feature", "image/png")
    client.put(
        f"{API}/features/{feature.id}", headers=headers, json={"image_id": own["id"]}
    )
    params = {"q": feature.name}
    listed = client.get(f"{API}/features/", headers=headers, params=params).json()
    # Without pieces the feature shows its own image.
    assert listed["data"][0]["cover_image"]["id"] == own["id"]
    assert listed["data"][0]["part_count"] == 0

    # No explicit order: codes in natural order, P2 before P10, everywhere.
    token = uuid.uuid4().hex[:6]
    p10 = create_random_part(db, code=f"{token}P10")
    p2 = create_random_part(db, code=f"{token}P2")
    for part in (p10, p2):
        crud_link = FeaturePartLink(feature_id=feature.id, part_id=part.id)
        db.add(crud_link)
    db.commit()
    image = upload(client, headers, "c.png", b"p2", "image/png")
    save(
        client,
        headers,
        str(feature.id),
        [{"part_id": str(p2.id), "image_id": image["id"]}],
    )
    page = detail(client, headers, str(feature.id))
    assert [cover["part_id"] for cover in page["part_covers"]] == [
        str(p2.id),
        str(p10.id),
    ]
    listed = client.get(f"{API}/features/", headers=headers, params=params).json()
    card = listed["data"][0]
    assert card["part_count"] == 2
    assert card["cover_image"]["id"] == image["id"]
    assert "part_covers" not in card


def test_an_expired_session_while_answering_saves_nothing(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The answer reads the CAD captures (SharePoint): if it fails, nothing was saved."""
    headers = superuser_token_headers
    feature_id, part_id, body = cover_example(client, headers, db)
    change = {"part_id": part_id, "image_id": body["image_id"]}
    assert save(client, headers, feature_id, [change]).status_code == 200
    before = detail(client, headers, feature_id)

    def expired(_: Any) -> str:
        raise HTTPException(401, "La sesión de Microsoft ha caducado.")

    monkeypatch.setattr(feature_covers, "document_cache_key", expired)
    # Removing the own cover makes the answer look for the CAD capture.
    result = save(client, headers, feature_id, [{"part_id": part_id}], name="Lost")
    assert result.status_code == 401
    other = create_random_part(db)
    result = client.post(
        f"{API}/features/{feature_id}/parts/{other.id}", headers=headers
    )
    assert result.status_code == 401
    monkeypatch.undo()
    after = detail(client, headers, feature_id)
    assert after["name"] == before["name"]
    assert after["part_covers"] == before["part_covers"]


def test_removing_the_step_waits_for_a_cover_being_saved(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both share the feature lock: the cover never keeps faces of a removed STEP."""
    headers = superuser_token_headers
    feature_id, part_id, body = cover_example(client, headers, db)
    validated, release = threading.Event(), threading.Event()
    real = feature_covers.validate_cover

    def slow(*args: Any) -> None:
        real(*args)
        validated.set()
        release.wait(10)

    monkeypatch.setattr(feature_covers, "validate_cover", slow)
    results: dict[str, int] = {}

    def save_cover() -> None:
        results["save"] = save(
            client, headers, feature_id, [{"part_id": part_id, **body}]
        ).status_code

    def remove_step() -> None:
        results["remove"] = client.delete(
            f"{API}/features/assets/{body['cover_3d']['asset_id']}", headers=headers
        ).status_code

    saving = threading.Thread(target=save_cover)
    saving.start()
    assert validated.wait(10)
    removing = threading.Thread(target=remove_step)
    removing.start()
    removing.join(0.5)
    # The removal waits for the save that already validated the STEP.
    assert removing.is_alive()
    release.set()
    saving.join(10)
    removing.join(10)
    assert results == {"save": 200, "remove": 200}
    cover = cover_of(detail(client, headers, feature_id), part_id)
    assert cover["image"]["id"] == body["image_id"]
    assert cover["cover_3d"] is None


def test_the_page_sends_the_cad_capture_also_under_an_own_cover(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Removing the own cover in the editor shows the CAD capture at once."""
    headers = superuser_token_headers
    feature_id, part_id, body = cover_example(client, headers, db)
    source = body["cover_3d"]
    capture = upload(client, headers, "auto.png", b"auto", "image/png")
    result = client.put(
        f"{API}/parts/{part_id}/cover",
        headers=headers,
        json={
            **{
                key: source[key] for key in ("file_id", "file_version", "source_sha256")
            },
            "image_id": capture["id"],
        },
    )
    assert result.status_code == 200, result.text
    save(client, headers, feature_id, [{"part_id": part_id, **body}])
    cover = cover_of(detail(client, headers, feature_id), part_id)
    assert cover["image"]["id"] == body["image_id"]
    assert cover["auto_image"]["id"] == capture["id"]
