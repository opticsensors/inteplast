"""Catalogue labels: measurements read by the app and features suggested by folder."""

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.measurement_models import MeasurementImport
from app.measurement_status import measurement_status
from app.models import Feature, FeaturePartLink, Part
from tests.utils.feature import create_random_part

API = settings.API_V1_STR


def valid_row(**changes: Any) -> dict[str, Any]:
    row = {
        "numbers": ["N170"],
        "value": 3.98,
        "source": {"path": "4- Metrologia/report.xls", "locator": "DR!F12"},
    }
    return {**row, **changes}


def add_import(
    db: Session, part: Part, rows: list[dict[str, Any]], **extra: Any
) -> None:
    values: dict[str, Any] = {
        "part_id": part.id,
        "fingerprint": uuid.uuid4().hex,
        "revision": "01",
        "sample": "01",
        "cavity": "c1",
        "source_path": part.folder_path or "piece",
        "source_id": "test",
        "sha256": "0" * 64,
        "reader": "test",
        "rows": rows,
    }
    db.add(MeasurementImport(**{**values, **extra}))
    db.commit()


def read(state: str, files: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "state": state,
        "imported": 0,
        "skipped": 0,
        "measurements": {"context_key": "", "files": []},
        "notices": [],
        "files": files or [],
    }


def test_measurement_status_follows_what_the_app_read(db: Session) -> None:
    unread = create_random_part(db)
    assert measurement_status(db, unread) is None

    # 2820: read finished, only a PDF and a STEP.
    nothing = create_random_part(db)
    nothing.last_read = read("ready")
    # 3226: a measurement report the reader could not interpret.
    pending = create_random_part(db)
    pending.last_read = read(
        "partial",
        [
            {
                "path": "4- Metrologia/Interns/x_intern.01.xls",
                "group": "measurements",
                "status": "Pendiente: las filas no tienen número de cota; hoja sin leer",
                "sheet": "DR",
            }
        ],
    )
    # 3212: values imported while the correction study is still running.
    running = create_random_part(db)
    running.last_read = read("processing")
    still = create_random_part(db)
    still.last_read = read("processing")
    failed = create_random_part(db)
    failed.last_read = read("error")
    db.add_all([nothing, pending, running, still, failed])
    db.commit()
    add_import(db, running, [valid_row()])

    assert measurement_status(db, nothing) == "none"
    assert measurement_status(db, pending) == "pending"
    assert measurement_status(db, running) == "detected"
    assert measurement_status(db, still) is None
    assert measurement_status(db, failed) is None


@pytest.mark.parametrize(
    "row",
    [
        valid_row(provenance_state="copia"),
        valid_row(flags=["copia"]),
        valid_row(value="3,98"),
        valid_row(value=None),
        valid_row(numbers=[]),
        valid_row(source={"path": "4- Metrologia/report.xls"}),
        valid_row(source={"locator": "DR!F12"}),
    ],
)
def test_only_valid_values_with_cota_and_source_count(
    db: Session, row: dict[str, Any]
) -> None:
    part = create_random_part(db)
    part.last_read = read(
        "ready", [{"path": "r.xls", "group": "measurements", "status": "imported"}]
    )
    db.add(part)
    db.commit()
    add_import(db, part, [row])
    # A report was found but nothing valid came out of it.
    assert measurement_status(db, part) == "pending"
    # A previous baseline does not count either.
    other = create_random_part(db)
    other.last_read = read("ready")
    db.add(other)
    db.commit()
    add_import(db, other, [valid_row()], baseline={"kind": "previous"})
    assert measurement_status(db, other) == "none"


def test_cards_carry_the_measurement_label(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    part = create_random_part(db)
    part.last_read = read("ready")
    db.add(part)
    db.commit()
    url = f"{API}/parts/{part.id}/detail"
    assert (
        client.get(url, headers=superuser_token_headers).json()["part"][
            "measurement_status"
        ]
        == "none"
    )
    add_import(db, part, [valid_row()])
    assert (
        client.get(url, headers=superuser_token_headers).json()["part"][
            "measurement_status"
        ]
        == "detected"
    )
    listed = client.get(
        f"{API}/catalog",
        headers=superuser_token_headers,
        params={"part_id": str(part.id), "kind": "part"},
    ).json()
    assert listed["parts"][0]["measurement_status"] == "detected"


@pytest.fixture
def folders(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, db: Session
) -> dict[str, Any]:
    monkeypatch.setattr(settings, "ASSETS_ROOT", str(tmp_path))
    monkeypatch.setattr(settings, "SHAREPOINT_ENABLED", False)
    token = uuid.uuid4().hex[:8]
    names = {
        "bolt": f"Bolt Eye {token}",
        "clips": f"Clips en Piezas {token}",
        "ribs": f"Nervios {token}",
        "twin_a": f"Gemelo {token}",
        "twin_b": f"gemelo  {token}",
    }
    features = {key: Feature(name=name) for key, name in names.items()}
    db.add_all(features.values())
    db.commit()
    paths = {
        "bolt": f"0- Bolt Eye {token}/3212 Pump Housing {token}",
        "bolt_case": f"0- bolt  EYE {token}/3197 Pot {token}",
        "clips": f"1- Clips en Piezas {token}/Tipo A/3174 {token}",
        "welding": f"5- Nervios de Soldadura {token}/3237 {token}",
        "twin": f"7- Gemelo {token}/3309 {token}",
        "root": f"3288 {token}",
    }
    for path in paths.values():
        (tmp_path / path).mkdir(parents=True)
    return {"features": features, "paths": paths, "token": token}


def test_features_are_suggested_by_exact_and_unique_folder_names(
    client: TestClient, superuser_token_headers: dict[str, str], folders: Any
) -> None:
    def suggested(key: str) -> list[str]:
        response = client.post(
            f"{API}/parts/discover",
            headers=superuser_token_headers,
            json={"folder_path": folders["paths"][key]},
        )
        assert response.status_code == 200, response.text
        return [item["id"] for item in response.json()["suggested_features"]]

    features = folders["features"]
    # The order prefix is not part of the name; case and spaces do not matter.
    assert suggested("bolt") == [str(features["bolt"].id)]
    assert suggested("bolt_case") == [str(features["bolt"].id)]
    # Intermediate folders count too.
    assert suggested("clips") == [str(features["clips"].id)]
    # «Nervios de Soldadura» is not «Nervios»: no partial matches.
    assert suggested("welding") == []
    # Two features with the same name: neither is suggested.
    assert suggested("twin") == []
    assert suggested("root") == []


def test_a_removed_suggestion_is_not_linked_when_the_piece_is_created(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    folders: Any,
) -> None:
    headers = superuser_token_headers
    path = folders["paths"]["bolt"]
    bolt = folders["features"]["bolt"]
    proposal = client.post(
        f"{API}/parts/discover", headers=headers, json={"folder_path": path}
    ).json()
    assert [item["id"] for item in proposal["suggested_features"]] == [str(bolt.id)]
    # Discovering never links anything.
    assert db.get(FeaturePartLink, (bolt.id, uuid.uuid4())) is None
    created = client.post(
        f"{API}/parts/register",
        headers=headers,
        json={
            "folder_path": path,
            "code": f"S{folders['token']}",
            "feature_ids": [],
        },
    )
    assert created.status_code == 200, created.text
    part_id = uuid.UUID(created.json()["id"])
    assert db.get(FeaturePartLink, (bolt.id, part_id)) is None
    # Asked again for the same folder: it is the user's choice, not re-applied.
    detail = client.get(f"{API}/parts/{part_id}/detail", headers=headers).json()
    assert detail["features"] == []


def reported_part(db: Session) -> Part:
    """A piece whose finished read found a measurement report."""
    part = create_random_part(db)
    part.last_read = read(
        "ready", [{"path": "r.xls", "group": "measurements", "status": "imported"}]
    )
    db.add(part)
    db.commit()
    return part


EARLIER = datetime(2026, 11, 1, tzinfo=timezone.utc)
LATER = EARLIER + timedelta(days=1)


def test_an_emptied_combination_no_longer_counts(db: Session) -> None:
    """A newer empty import of the same revision, sample and cavity retires its values."""
    part = reported_part(db)
    add_import(db, part, [valid_row()], imported_at=EARLIER)
    assert measurement_status(db, part) == "detected"
    add_import(db, part, [], imported_at=LATER)
    assert measurement_status(db, part) == "pending"


def test_another_combination_with_a_value_keeps_the_label(db: Session) -> None:
    part = reported_part(db)
    add_import(db, part, [valid_row()], imported_at=EARLIER, cavity="c1")
    add_import(db, part, [valid_row()], imported_at=EARLIER, cavity="c2")
    add_import(db, part, [], imported_at=LATER, cavity="c1")
    assert measurement_status(db, part) == "detected"
    add_import(db, part, [], imported_at=LATER, cavity="c2")
    assert measurement_status(db, part) == "pending"


def test_same_import_time_is_settled_by_id_as_in_the_history(db: Session) -> None:
    from app.measurement_imports import history_summary

    emptied, kept = reported_part(db), reported_part(db)
    # Same instant: the history keeps the import with the greater id.
    add_import(db, emptied, [valid_row()], imported_at=EARLIER, id=uuid.UUID(int=1))
    add_import(db, emptied, [], imported_at=EARLIER, id=uuid.UUID(int=2))
    add_import(db, kept, [], imported_at=EARLIER, id=uuid.UUID(int=3))
    add_import(db, kept, [valid_row()], imported_at=EARLIER, id=uuid.UUID(int=4))
    for part, expected, active_id in (
        (emptied, "pending", uuid.UUID(int=2)),
        (kept, "detected", uuid.UUID(int=4)),
    ):
        active = [row.id for row in history_summary(db, part.id) if row.active]
        assert active == [active_id]
        assert measurement_status(db, part) == expected
