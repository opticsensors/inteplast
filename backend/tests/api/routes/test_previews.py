import io
import json
import struct
import threading
import uuid
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import trimesh
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session

from app import previews
from app.core.config import settings
from app.core.db import engine
from app.models import FilePreview, StoredFile
from app.preview_converter import convert, sha256

BASE = f"{settings.API_V1_STR}/files"


def test_step_reduction_preserves_a_closed_surface(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.preview_converter as converter

    mesh = trimesh.creation.icosphere(subdivisions=8)
    original_volume = mesh.volume
    # Reproduce the separate vertex arrays emitted for adjacent CAD faces.
    mesh.unmerge_vertices()
    monkeypatch.setattr(converter, "step_mesh", lambda _path: mesh)
    source, output = tmp_path / "synthetic.step", tmp_path / "web.glb"
    source.write_bytes(b"Synthetic tessellation fixture")
    result = convert(source, ".step", output)
    assert result["triangles"] <= 500000
    reduced = trimesh.load(output).to_mesh()
    assert reduced.is_watertight
    assert abs(reduced.volume - original_volume) / original_volume < 0.01


@pytest.fixture
def original(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> dict[str, Any]:
    data = trimesh.creation.icosphere(subdivisions=2).export(file_type="stl")
    response = client.post(
        BASE + "/",
        headers=superuser_token_headers,
        files={"file": ("synthetic.stl", data, "model/stl")},
    )
    assert response.status_code == 200
    return response.json()  # type: ignore[no-any-return]


def test_preview_queue_cache_auth_and_original(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
    original: dict[str, Any],
) -> None:
    file_id = original["id"]
    endpoint = f"{BASE}/{file_id}/preview"
    headers = superuser_token_headers
    source = settings.uploads_path / file_id
    digest = sha256(source)
    assert client.post(endpoint).status_code == 401
    assert client.get(endpoint).status_code == 401
    assert client.post(endpoint, headers=headers).json()["state"] == "queued"
    assert client.post(endpoint, headers=headers).json()["state"] == "queued"
    # A persisted interrupted job is picked up again (same path as a restart).
    job = db.get(FilePreview, uuid.UUID(file_id))
    assert job is not None
    job.state = "processing"
    db.add(job)
    db.commit()
    assert previews.process_next(threading.Event())
    ready = client.post(endpoint, headers=headers).json()
    assert ready["state"] == "ready", ready
    response = client.get(ready["url"])
    assert response.status_code == 200
    assert response.content[:4] == b"glTF"
    scene = trimesh.load(io.BytesIO(response.content), file_type="glb")
    assert np.allclose(scene.bounds, [[-1, -1, -1], [1, 1, 1]], atol=0.01)
    assert client.get(ready["url"], headers={"Range": "bytes=0-3"}).content == b"glTF"
    original_url = client.get(f"{BASE}/{file_id}/access-url", headers=headers).json()[
        "url"
    ]
    assert sha256(source) == digest
    assert client.get(original_url).content == source.read_bytes()
    assert client.get(ready["url"].replace("/preview?", "?")).status_code == 401
    assert (
        client.get(original_url.replace("?token", "/preview?token")).status_code == 401
    )
    assert (
        client.get(ready["url"].replace(file_id, str(uuid.uuid4()))).status_code == 401
    )
    db.expire_all()
    job = db.get(FilePreview, uuid.UUID(file_id))
    assert job is not None
    path = previews.preview_path(job)
    before = path.stat().st_mtime_ns
    assert client.post(endpoint, headers=headers).json()["state"] == "ready"
    assert path.stat().st_mtime_ns == before
    assert path.with_suffix(".json").is_file()
    # Disposable cache can be regenerated without re-uploading.
    path.unlink()
    assert client.post(endpoint, headers=headers).json()["state"] == "queued"
    client.delete(f"{BASE}/{file_id}", headers=headers)
    assert not path.parent.exists()


def test_failed_conversion_can_retry(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = superuser_token_headers
    file_id = client.post(
        BASE + "/", headers=headers, files={"file": ("broken.stl", b"not geometry")}
    ).json()["id"]
    endpoint = f"{BASE}/{file_id}/preview"
    client.post(endpoint, headers=headers)
    previews.process_next(threading.Event())
    error = client.post(endpoint, headers=headers).json()
    assert error["state"] == "error"
    assert "Traceback" not in error["message"]
    assert (
        client.post(endpoint + "?retry=true", headers=headers).json()["state"]
        == "queued"
    )
    # Timeout/cancellation always terminates the child process.
    monkeypatch.setattr(settings, "PREVIEW_TIMEOUT_SECONDS", 0)
    previews.process_next(threading.Event())
    assert client.post(endpoint, headers=headers).json()["state"] == "error"
    client.delete(f"{BASE}/{file_id}", headers=headers)


def test_partial_preview_warning_reaches_the_viewer(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    original: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    converter = previews.run_converter

    def partial(*args: Any) -> dict[str, Any]:
        return {**converter(*args), "step_incomplete_faces": [1]}

    monkeypatch.setattr(previews, "run_converter", partial)
    endpoint = f"{BASE}/{original['id']}/preview"
    client.post(endpoint, headers=superuser_token_headers)
    assert previews.process_next(threading.Event())
    ready = client.post(endpoint, headers=superuser_token_headers).json()
    assert ready["state"] == "ready"
    assert ready["message"].startswith("Vista parcial:")
    assert client.get(ready["url"]).status_code == 200
    client.delete(f"{BASE}/{original['id']}", headers=superuser_token_headers)


@pytest.mark.parametrize("boxes", [1, 20])
def test_missing_step_faces_are_reported_or_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boxes: int
) -> None:
    from types import SimpleNamespace

    import OCP.BRepMesh
    from OCP.BRep import BRep_Builder
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.gp import gp_Pnt
    from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
    from OCP.TopoDS import TopoDS_Compound

    compound = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(compound)
    for index in range(boxes):
        builder.Add(
            compound, BRepPrimAPI_MakeBox(gp_Pnt(index * 2, 0, 0), 1, 1, 1).Shape()
        )
    source, output = tmp_path / "partial.step", tmp_path / "partial.glb"
    writer = STEPControl_Writer()
    writer.Transfer(compound, STEPControl_AsIs)
    writer.Write(str(source))
    native_mesher = OCP.BRepMesh.BRepMesh_IncrementalMesh
    calls = 0

    def missing_first_face(*args: Any) -> Any:
        nonlocal calls
        calls += 1
        # Initial assembly mesh and every repair attempt for its first face.
        if calls <= 4:
            return SimpleNamespace(IsDone=lambda: True)
        return native_mesher(*args)

    monkeypatch.setattr(OCP.BRepMesh, "BRepMesh_IncrementalMesh", missing_first_face)
    if boxes == 1:
        with pytest.raises(ValueError, match="More than 1%"):
            convert(source, ".step", output)
        assert not output.exists()
    else:
        result = convert(source, ".step", output)
        assert result["step_faces"] == 120
        assert result["step_incomplete_faces"] == [1]
        assert result["triangles"] == 238
        assert output.is_file()


def test_changed_local_source_invalidates_preview(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "scan.stl"
    source.write_bytes(trimesh.creation.box().export(file_type="stl"))
    monkeypatch.setattr(settings, "ASSETS_ROOT", str(tmp_path))
    monkeypatch.setattr(settings, "ASSETS_SOURCE_ID", str(uuid.uuid4()))
    headers = superuser_token_headers
    file = client.post(
        f"{BASE}/reference", headers=headers, json={"path": source.name}
    ).json()
    endpoint = f"{BASE}/{file['id']}/preview"
    client.post(endpoint, headers=headers)
    previews.process_next(threading.Event())
    ready = client.post(endpoint, headers=headers).json()
    assert ready["state"] == "ready", ready
    source.write_bytes(trimesh.creation.box(extents=[2, 2, 2]).export(file_type="stl"))
    assert client.get(ready["url"]).status_code == 409
    assert client.post(endpoint, headers=headers).status_code == 409
    relink = client.put(
        f"{BASE}/{file['id']}/reference",
        headers=headers,
        json={"path": source.name, "expected_version": file["version"]},
    )
    assert relink.status_code == 200
    assert client.get(ready["url"]).status_code == 401
    assert client.post(endpoint, headers=headers).json()["state"] == "queued"
    # A change while a native job is running must not publish stale geometry.
    converter = previews.run_converter

    def changing_converter(*args: Any) -> dict[str, Any]:
        result = converter(*args)
        source.write_bytes(
            trimesh.creation.box(extents=[3, 3, 3]).export(file_type="stl")
        )
        return result

    monkeypatch.setattr(previews, "run_converter", changing_converter)
    previews.process_next(threading.Event())
    db.expire_all()
    job = db.get(FilePreview, uuid.UUID(file["id"]))
    assert job is not None and job.state == "error"
    client.delete(f"{BASE}/{file['id']}", headers=headers)
    assert source.is_file()


@pytest.mark.parametrize("skip_mesh_calls", [0, 1, 2])
def test_step_assembly_locations_and_winding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    skip_mesh_calls: int,
) -> None:
    from types import SimpleNamespace

    import OCP.BRepMesh
    from OCP.BRep import BRep_Builder
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.gp import gp_Trsf, gp_Vec
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS_Compound

    compound = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(compound)
    box = BRepPrimAPI_MakeBox(1, 2, 3).Shape()
    transform = gp_Trsf()
    transform.SetTranslation(gp_Vec(10, 0, 0))
    builder.Add(compound, box)
    builder.Add(compound, box.Moved(TopLoc_Location(transform)))
    writer = STEPControl_Writer()
    writer.Transfer(compound, STEPControl_AsIs)
    source = tmp_path / "assembly.step"
    assert writer.Write(str(source)) == IFSelect_RetDone
    digest = sha256(source)
    output = tmp_path / "view.glb"
    native_mesher = OCP.BRepMesh.BRepMesh_IncrementalMesh
    calls = 0

    def delayed_mesher(*args: Any) -> Any:
        nonlocal calls
        calls += 1
        if calls <= skip_mesh_calls:
            return SimpleNamespace(IsDone=lambda: True)
        return native_mesher(*args)

    monkeypatch.setattr(OCP.BRepMesh, "BRepMesh_IncrementalMesh", delayed_mesher)
    metadata = convert(source, ".step", output)
    assert metadata["triangles"] == 24
    assert metadata["step_faces"] == 12
    assert (metadata["step_retried_faces"] > 0) == (skip_mesh_calls > 0)
    assert (metadata["step_repaired_faces"] > 0) == (skip_mesh_calls > 1)
    assert metadata["source_sha256"] == digest == sha256(source)
    scene = trimesh.load(output)
    assert np.allclose(scene.bounds, [[0, 0, 0], [11, 2, 3]])
    mesh = scene.to_mesh()
    assert mesh.volume == pytest.approx(12)


def test_preview_rejects_unsupported_and_oversize(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
    original: dict[str, Any],
) -> None:
    file = db.get(StoredFile, uuid.UUID(original["id"]))
    assert file is not None
    file.size = 513 * 1024 * 1024
    db.add(file)
    db.commit()
    endpoint = f"{BASE}/{file.id}/preview"
    assert client.post(endpoint, headers=superuser_token_headers).status_code == 413
    file.filename = "model.mfr"
    db.add(file)
    db.commit()
    assert client.post(endpoint, headers=superuser_token_headers).status_code == 415
    client.delete(f"{BASE}/{file.id}", headers=superuser_token_headers)


def test_workers_share_one_conversion_lock(monkeypatch: pytest.MonkeyPatch) -> None:
    stop = threading.Event()
    entered = threading.Event()
    calls = []

    def fake_process(_stop: threading.Event) -> bool:
        calls.append(1)
        entered.set()
        stop.wait(5)
        return False

    monkeypatch.setattr(previews, "process_next", fake_process)
    with Session(engine) as lock_session:
        assert lock_session.execute(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": previews.WORKER_LOCK}
        ).scalar()
        workers = [
            threading.Thread(target=previews.worker, args=(stop,)) for _ in range(2)
        ]
        try:
            for worker in workers:
                worker.start()
            assert not entered.wait(0.3)
            lock_session.execute(
                text("SELECT pg_advisory_unlock(:key)"), {"key": previews.WORKER_LOCK}
            )
            assert entered.wait(4)
            assert not stop.wait(0.3)
            assert len(calls) == 1
        finally:
            stop.set()
            for worker in workers:
                worker.join(timeout=5)
    assert all(not worker.is_alive() for worker in workers)


def test_decimation_has_finite_normals_without_quadratic_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_fallback(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("Do not scan all faces once per vertex")

    source = tmp_path / "dense.stl"
    source.write_bytes(
        trimesh.creation.icosphere(subdivisions=7).export(file_type="stl")
    )
    monkeypatch.setattr(trimesh.geometry, "weighted_vertex_normals", no_fallback)
    output = tmp_path / "dense.glb"
    result = convert(source, ".stl", output)
    assert result["source_triangles"] == 327680
    assert 0 < result["triangles"] <= 300000
    data = output.read_bytes()
    json_length = struct.unpack_from("<I", data, 12)[0]
    gltf = json.loads(data[20 : 20 + json_length])
    index = gltf["meshes"][0]["primitives"][0]["attributes"]["NORMAL"]
    accessor = gltf["accessors"][index]
    view = gltf["bufferViews"][accessor["bufferView"]]
    offset = (
        28 + json_length + view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    )
    normals = np.frombuffer(
        data, dtype="<f4", count=accessor["count"] * 3, offset=offset
    ).reshape(-1, 3)
    assert np.isfinite(normals).all()
    assert np.allclose(np.linalg.norm(normals, axis=1), 1, atol=1e-5)
