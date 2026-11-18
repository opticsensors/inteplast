import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import FeatureAsset, FeaturePartLink, Part, StoredFile
from tests.utils.feature import (
    create_random_asset,
    create_random_feature,
    create_random_part,
)
from tests.utils.utils import random_lower_string


def test_create_part_and_reject_duplicate_code(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    code = random_lower_string()
    response = client.post(
        f"{settings.API_V1_STR}/parts/",
        headers=superuser_token_headers,
        json={"code": code, "name": "Pump Housing"},
    )
    assert response.status_code == 200
    assert response.json()["code"] == code

    response = client.post(
        f"{settings.API_V1_STR}/parts/",
        headers=superuser_token_headers,
        json={"code": code, "name": "otra cosa"},
    )
    assert response.status_code == 409


def test_read_parts(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    part = create_random_part(db)
    response = client.get(
        f"{settings.API_V1_STR}/parts/", headers=superuser_token_headers
    )
    assert response.status_code == 200
    content = response.json()
    assert part.code in [item["code"] for item in content["data"]]


def test_update_part(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    part = create_random_part(db)
    other = create_random_part(db)

    response = client.put(
        f"{settings.API_V1_STR}/parts/{part.id}",
        headers=superuser_token_headers,
        json={"name": "Pump Housing"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Pump Housing"

    response = client.put(
        f"{settings.API_V1_STR}/parts/{part.id}",
        headers=superuser_token_headers,
        json={"code": other.code},
    )
    assert response.status_code == 409


def test_update_part_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.put(
        f"{settings.API_V1_STR}/parts/{uuid.uuid4()}",
        headers=superuser_token_headers,
        json={"name": "x"},
    )
    assert response.status_code == 404


def test_delete_part_needs_superuser(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    part = create_random_part(db)
    response = client.delete(
        f"{settings.API_V1_STR}/parts/{part.id}", headers=normal_user_token_headers
    )
    assert response.status_code == 403


def test_delete_part_rejects_implicit_asset_usage(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    """Assets alone count as usage, even without an explicit feature link."""
    feature = create_random_feature(db)
    part = create_random_part(db)
    asset = create_random_asset(db, feature, part=part)

    response = client.delete(
        f"{settings.API_V1_STR}/parts/{part.id}", headers=superuser_token_headers
    )
    assert response.status_code == 409

    db.expire_all()
    stored = db.get(FeatureAsset, asset.id)
    assert stored is not None
    assert stored.part_id == part.id
    assert db.get(Part, part.id) is not None


def test_usage_counts_distinct_features_and_blocks_explicit_links(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    part, unused = create_random_part(db), create_random_part(db)
    first, second = create_random_feature(db), create_random_feature(db)
    db.add(FeaturePartLink(feature_id=first.id, part_id=part.id))
    db.add(FeaturePartLink(feature_id=second.id, part_id=part.id))
    db.commit()
    create_random_asset(db, first, part=part)
    create_random_asset(db, first, part=part)
    # Every piece: other tests add many, and the list is paged by code.
    listed = client.get(
        f"{settings.API_V1_STR}/parts/",
        headers=superuser_token_headers,
        params={"limit": 100000},
    ).json()["data"]
    counts = {row["id"]: row["feature_count"] for row in listed}
    assert counts[str(part.id)] == 2
    assert counts[str(unused.id)] == 0
    response = client.delete(
        f"{settings.API_V1_STR}/parts/{part.id}", headers=superuser_token_headers
    )
    assert response.status_code == 409
    assert "2 features" in response.json()["detail"]
    assert db.get(FeaturePartLink, (second.id, part.id)) is not None


def test_delete_unused_part_removes_only_catalog_entry(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    tmp_path: Path,
) -> None:
    part = create_random_part(db)
    part.folder_path = "Trial piece"
    db.add(part)
    folder = tmp_path / part.folder_path
    folder.mkdir()
    original = folder / "drawing.pdf"
    original.write_bytes(b"synthetic original")
    document = StoredFile(
        filename="drawing.pdf", size=18, content_type="application/pdf"
    )
    db.add(document)
    db.commit()
    part_id, document_id = part.id, document.id
    response = client.delete(
        f"{settings.API_V1_STR}/parts/{part_id}", headers=superuser_token_headers
    )
    assert response.status_code == 200
    db.expire_all()
    assert db.get(Part, part_id) is None
    assert db.get(StoredFile, document_id) is not None
    assert original.read_bytes() == b"synthetic original"
    listed = client.get(
        f"{settings.API_V1_STR}/parts/", headers=superuser_token_headers
    ).json()["data"]
    assert str(part_id) not in {row["id"] for row in listed}
    assert (
        client.delete(
            f"{settings.API_V1_STR}/parts/{part_id}", headers=superuser_token_headers
        ).status_code
        == 404
    )


def _piece_with_data(db: Session, tmp_path: Path) -> dict[str, Any]:
    """A piece with cotas, measurements, own and shared documents and two features."""
    from app.knowledge_models import (
        DrawingLocation,
        EvidenceJob,
        FeatureCharacteristicLink,
        PartCharacteristic,
        PartDocument,
        PartFile,
        PartReference,
    )
    from app.measurement_models import MeasurementImport

    part, other = create_random_part(db), create_random_part(db)
    part.folder_path = f"Piece {part.code}"
    folder = tmp_path / part.folder_path
    folder.mkdir()
    original = folder / "drawing.pdf"
    original.write_bytes(b"synthetic original")
    own = StoredFile(
        filename="drawing.pdf",
        source="local",
        source_path=f"{part.folder_path}/drawing.pdf",
        content_type="application/pdf",
    )
    upload = StoredFile(filename="photo.png", source="upload", content_type="image/png")
    shared = StoredFile(filename="shared.step", source="local", source_path="x.step")
    first, second = create_random_feature(db), create_random_feature(db)
    db.add_all([part, own, upload, shared])
    db.flush()
    uploaded = settings.uploads_path / str(upload.id)
    uploaded.parent.mkdir(parents=True, exist_ok=True)
    uploaded.write_bytes(b"uploaded bytes")
    cota = PartCharacteristic(part_id=part.id, code="N1", revision="01")
    other_cota = PartCharacteristic(part_id=other.id, code="N1", revision="01")
    db.add_all([cota, other_cota])
    db.flush()
    asset = FeatureAsset(
        feature_id=first.id, part_id=part.id, file_id=own.id, kind="drawing", name="d"
    )
    db.add_all(
        [
            FeaturePartLink(feature_id=first.id, part_id=part.id),
            FeaturePartLink(feature_id=first.id, part_id=other.id),
            FeatureCharacteristicLink(feature_id=first.id, characteristic_id=cota.id),
            FeatureCharacteristicLink(
                feature_id=first.id, characteristic_id=other_cota.id
            ),
            asset,
            PartDocument(part_id=part.id, file_id=own.id, kind="reference_drawing"),
            PartFile(part_id=part.id, file_id=upload.id, kind="other", name="photo"),
            PartReference(part_id=part.id, kind="drawing", file_id=own.id),
            PartFile(part_id=part.id, file_id=shared.id, kind="part", name="cad"),
            PartFile(part_id=other.id, file_id=shared.id, kind="part", name="cad"),
            MeasurementImport(
                part_id=part.id,
                fingerprint=uuid.uuid4().hex,
                revision="01",
                sample="01",
                cavity="c1",
                source_path=part.folder_path,
                source_id="test",
                sha256="0" * 64,
                reader="test",
                rows=[],
            ),
            EvidenceJob(id=uuid.uuid4(), kind="drawing", file_id=own.id, cache_key="k"),
            EvidenceJob(id=uuid.uuid4(), kind="study", part_id=part.id, cache_key="k"),
            DrawingLocation(
                file_id=own.id,
                sha256="0" * 64,
                candidate_id="c",
                label="N1",
                page=1,
                box=[0, 0, 1, 1],
            ),
        ]
    )
    db.flush()
    first.part_order = [str(other.id), str(part.id)]
    first.cover_3d = {"asset_id": str(asset.id), "part_id": str(part.id)}
    second.part_order = [str(part.id)]
    db.add_all([first, second])
    db.add(FeatureAsset(feature_id=second.id, part_id=part.id, kind="mold", name="m"))
    db.commit()
    return {
        "part": part.id,
        "other": other.id,
        "first": first.id,
        "second": second.id,
        "own": own.id,
        "upload": upload.id,
        "shared": shared.id,
        "cota": cota.id,
        "other_cota": other_cota.id,
        "original": original,
        "uploaded": uploaded,
    }


def test_deletion_scope_and_full_deletion_keep_features_and_originals(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    normal_user_token_headers: dict[str, str],
    db: Session,
    tmp_path: Path,
) -> None:
    from app.knowledge_models import (
        DrawingLocation,
        EvidenceJob,
        FeatureCharacteristicLink,
        PartCharacteristic,
        PartDocument,
        PartFile,
        PartReference,
    )
    from app.measurement_models import MeasurementImport
    from app.models import Feature

    ids = _piece_with_data(db, tmp_path)
    part_id = ids["part"]
    url = f"{settings.API_V1_STR}/parts/{part_id}"
    assert (
        client.get(f"{url}/deletion", headers=normal_user_token_headers).status_code
        == 403
    )
    scope = client.get(f"{url}/deletion", headers=superuser_token_headers).json()
    assert {f["id"] for f in scope["features"]} == {
        str(ids["first"]),
        str(ids["second"]),
    }
    assert scope["characteristics"] == 1
    assert scope["feature_characteristic_links"] == 1
    assert scope["measurement_imports"] == 1
    assert scope["feature_assets"] == 2
    assert scope["covers_reset"] == 1
    assert scope["files_removed"] == 2  # The drawing reference and the upload.
    assert scope["uploads_removed"] == 1
    assert scope["files_kept"] == 1  # Also used by another piece.
    assert scope["reviewed_locations"] == 1
    assert scope["jobs"] == 2

    # Without the key only an unused piece can be deleted; never by a normal user.
    assert client.delete(url, headers=superuser_token_headers).status_code == 409
    assert (
        client.delete(
            url, headers=normal_user_token_headers, params={"confirm": scope["key"]}
        ).status_code
        == 403
    )
    assert (
        client.delete(
            url, headers=superuser_token_headers, params={"confirm": "0" * 64}
        ).status_code
        == 409
    )
    db.expire_all()
    assert db.get(Part, part_id) is not None
    assert db.get(StoredFile, ids["own"]) is not None

    response = client.delete(
        url, headers=superuser_token_headers, params={"confirm": scope["key"]}
    )
    assert response.status_code == 200, response.text
    assert response.json()["scope"]["key"] == scope["key"]
    db.expire_all()
    assert db.get(Part, part_id) is None
    assert db.get(Part, ids["other"]) is not None
    first, second = db.get(Feature, ids["first"]), db.get(Feature, ids["second"])
    assert first is not None and second is not None
    assert first.part_order == [str(ids["other"])] and second.part_order == []
    assert first.cover_3d is None
    assert db.get(FeaturePartLink, (ids["first"], ids["other"])) is not None
    assert db.get(PartCharacteristic, ids["other_cota"]) is not None
    assert db.get(FeatureCharacteristicLink, (ids["first"], ids["other_cota"]))
    assert db.get(FeatureCharacteristicLink, (ids["first"], ids["cota"])) is None
    assert db.get(StoredFile, ids["own"]) is None
    assert db.get(StoredFile, ids["upload"]) is None
    assert db.get(StoredFile, ids["shared"]) is not None
    assert ids["original"].read_bytes() == b"synthetic original"
    assert not ids["uploaded"].exists()
    for model in (
        MeasurementImport,
        PartCharacteristic,
        PartDocument,
        PartFile,
        PartReference,
        FeaturePartLink,
        FeatureAsset,
        EvidenceJob,
    ):
        assert not db.exec(select(model).where(model.part_id == part_id)).all()  # type: ignore[attr-defined]
    for model in (EvidenceJob, DrawingLocation):
        assert not db.exec(select(model).where(model.file_id == ids["own"])).all()  # type: ignore[attr-defined]
    assert (
        client.get(f"{url}/deletion", headers=superuser_token_headers).status_code
        == 404
    )


def test_deletion_key_changes_with_the_data(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    from app.knowledge_models import PartCharacteristic

    part = create_random_part(db)
    url = f"{settings.API_V1_STR}/parts/{part.id}"
    before = client.get(f"{url}/deletion", headers=superuser_token_headers).json()
    db.add(PartCharacteristic(part_id=part.id, code="N2", revision="01"))
    db.commit()
    response = client.delete(
        url, headers=superuser_token_headers, params={"confirm": before["key"]}
    )
    assert response.status_code == 409
    assert "alcance" in response.json()["detail"]
    db.expire_all()
    assert db.get(Part, part.id) is not None


def test_deletion_keeps_an_image_shown_in_a_feature_note(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    from app.models import FeatureNote, NoteKind

    part, feature = create_random_part(db), create_random_feature(db)
    image = StoredFile(filename="defect.png", source="upload", content_type="image/png")
    db.add(image)
    db.flush()
    stored = settings.uploads_path / str(image.id)
    stored.parent.mkdir(parents=True, exist_ok=True)
    stored.write_bytes(b"image bytes")
    db.add_all(
        [
            FeatureAsset(
                feature_id=feature.id,
                part_id=part.id,
                file_id=image.id,
                kind="drawing",
                name="defect",
            ),
            FeatureNote(
                feature_id=feature.id,
                kind=NoteKind.warning,
                title="Rechupe",
                body=f"Ver foto:\n\n![defect.png](file:{image.id})",
            ),
        ]
    )
    db.commit()
    part_id, image_id = part.id, image.id
    url = f"{settings.API_V1_STR}/parts/{part_id}"
    scope = client.get(f"{url}/deletion", headers=superuser_token_headers).json()
    assert scope["files_removed"] == 0
    assert scope["files_kept"] == 1
    response = client.delete(
        url, headers=superuser_token_headers, params={"confirm": scope["key"]}
    )
    assert response.status_code == 200, response.text
    db.expire_all()
    assert db.get(Part, part_id) is None
    assert db.get(StoredFile, image_id) is not None
    assert stored.read_bytes() == b"image bytes"


@pytest.mark.parametrize("change", ["location", "characteristic", "measurement"])
def test_deletion_key_changes_when_a_deleted_row_is_edited(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    tmp_path: Path,
    change: str,
) -> None:
    """Same counts, different content: the old confirmation is no longer valid."""
    from app.knowledge_models import DrawingLocation, PartCharacteristic
    from app.measurement_models import MeasurementImport

    ids = _piece_with_data(db, tmp_path)
    url = f"{settings.API_V1_STR}/parts/{ids['part']}"
    before = client.get(f"{url}/deletion", headers=superuser_token_headers).json()
    if change == "location":
        row: Any = db.exec(
            select(DrawingLocation).where(DrawingLocation.file_id == ids["own"])
        ).one()
        row.label = "N2"
    elif change == "characteristic":
        row = db.get(PartCharacteristic, ids["cota"])
        row.code = "N3"
    else:
        row = db.exec(
            select(MeasurementImport).where(MeasurementImport.part_id == ids["part"])
        ).one()
        row.sample = "02"
    db.add(row)
    db.commit()
    after = client.get(f"{url}/deletion", headers=superuser_token_headers).json()
    assert {k: v for k, v in after.items() if k != "key"} == {
        k: v for k, v in before.items() if k != "key"
    }
    response = client.delete(
        url, headers=superuser_token_headers, params={"confirm": before["key"]}
    )
    assert response.status_code == 409
    db.expire_all()
    assert db.get(Part, ids["part"]) is not None
