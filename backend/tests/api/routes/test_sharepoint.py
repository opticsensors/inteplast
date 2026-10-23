"""SharePoint source and Microsoft sign-in, with Graph and MSAL simulated (no network)."""

import uuid
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlsplit

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import microsoft_auth, sharepoint
from app.core.config import settings
from app.core.db import engine
from app.file_sources import reference_key
from app.measurement_models import MeasurementImport
from app.models import Part, StoredFile
from app.pilot import is_pilot
from app.rebase_source import RebaseError, rebase
from app.source_types import SourceError

API = settings.API_V1_STR
PIECE = "0- Bolt Eye/3212 Pump Housing"


class FakeGraph:
    """A drive whose `Root Folder` holds the dataset, served through httpx."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {
            f"{PIECE}/plan #1.pdf": b"%PDF graph v1",
            f"{PIECE}/4- Metrologia/a.csv": b"N1;x\n",
        }
        self.versions: dict[str, int] = dict.fromkeys(self.files, 1)
        self.requests: list[httpx.Request] = []
        self.downloads = 0
        self.fail: list[int] = []

    def folders(self) -> set[str]:
        result = {""}
        for path in self.files:
            parts = path.split("/")
            result.update("/".join(parts[:i]) for i in range(1, len(parts)))
        return result

    def meta(self, path: str) -> dict[str, Any]:
        name = path.rsplit("/", 1)[-1] if path else "Root Folder"
        data: dict[str, Any] = {
            "id": f"id-{path}",
            "name": name,
            "parentReference": {"driveId": "drive-1"},
        }
        if path in self.files:
            data.update(
                file={},
                size=len(self.files[path]),
                cTag=f"c-{self.versions[path]}",
                **{
                    "@microsoft.graph.downloadUrl": f"https://download.test/{quote(path)}"
                },
            )
        else:
            data["folder"] = {}
        return data

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.fail:
            status = self.fail.pop(0)
            return httpx.Response(status, headers={"Retry-After": "0"}, json={})
        if request.url.host == "download.test":
            self.downloads += 1
            return httpx.Response(200, content=self.files[request.url.path[1:]])
        raw = request.url.raw_path.decode().split("?")[0]
        prefix = "/v1.0/me/drive/root:/Root%20Folder"
        assert raw.startswith(prefix), raw
        rest = raw[len(prefix) :]
        listing = rest.endswith(":/children")
        path = unquote(rest.removesuffix(":/children").removesuffix(":")).strip("/")
        if path not in self.files and path not in self.folders():
            return httpx.Response(404, json={})
        if not listing:
            return httpx.Response(200, json=self.meta(path))
        entries = {
            p.split("/")[len(path.split("/")) if path else 0]
            for p in self.files
            if not path or p.startswith(f"{path}/")
        }
        children = ["/".join(filter(None, [path, name])) for name in sorted(entries)]
        return httpx.Response(200, json={"value": [self.meta(c) for c in children]})


@pytest.fixture
def graph(monkeypatch: pytest.MonkeyPatch) -> FakeGraph:
    fake = FakeGraph()
    graph_client = httpx.Client(transport=httpx.MockTransport(fake))
    monkeypatch.setattr(settings, "SHAREPOINT_ENABLED", True)
    monkeypatch.setattr(settings, "SHAREPOINT_ROOT_PATH", "Root Folder")
    monkeypatch.setattr(settings, "SHAREPOINT_DRIVE_ID", None)
    monkeypatch.setattr(settings, "ASSETS_SOURCE_ID", f"sharepoint-{uuid.uuid4()}")
    monkeypatch.setattr(sharepoint, "client", lambda: graph_client)
    monkeypatch.setattr(sharepoint, "access_token", lambda user_id: f"t-{user_id}")
    monkeypatch.setattr(sharepoint.time, "sleep", lambda _seconds: None)
    return fake


def test_sharepoint_browses_links_and_serves_latest_version(
    client: TestClient, superuser_token_headers: dict[str, str], graph: FakeGraph
) -> None:
    headers = superuser_token_headers
    me = client.get(f"{API}/users/me", headers=headers).json()
    listing = client.get(
        f"{API}/files/source", headers=headers, params={"path": PIECE}
    ).json()
    assert [(e["name"], e["directory"]) for e in listing["entries"]] == [
        ("4- Metrologia", True),
        ("plan #1.pdf", False),
    ]
    # Graph is read with the token of the user who made the request.
    assert graph.requests[-1].headers["Authorization"] == f"Bearer t-{me['id']}"

    path = f"{PIECE}/plan #1.pdf"
    linked = client.post(f"{API}/files/reference", headers=headers, json={"path": path})
    assert linked.status_code == 200, linked.text
    document = linked.json()
    stored = client.get(f"{API}/files/{document['id']}/status", headers=headers)
    assert stored.json()["state"] == "available"
    assert any(b"plan%20%231.pdf" in r.url.raw_path for r in graph.requests)

    content = client.get(f"{API}/files/{document['id']}", headers=headers)
    assert content.content == b"%PDF graph v1"
    client.get(f"{API}/files/{document['id']}", headers=headers)
    assert graph.downloads == 1  # Cached per version.

    graph.files[path], graph.versions[path] = b"%PDF graph v2", 2
    assert (
        client.get(f"{API}/files/{document['id']}", headers=headers).content
        == b"%PDF graph v2"
    )
    relinked = client.post(
        f"{API}/files/reference", headers=headers, json={"path": path}
    )
    assert relinked.json()["id"] == document["id"]  # One document per path.

    del graph.files[path]
    missing = client.get(f"{API}/files/{document['id']}/status", headers=headers)
    assert missing.json()["state"] == "missing"


def test_graph_throttling_permissions_and_expired_sessions(
    client: TestClient, superuser_token_headers: dict[str, str], graph: FakeGraph
) -> None:
    url, headers = f"{API}/files/source", superuser_token_headers
    graph.fail = [429, 503]
    assert client.get(url, headers=headers).status_code == 200
    graph.fail = [403]
    # Not 403: that status would close the application session.
    assert client.get(url, headers=headers).status_code == 409
    graph.fail = [401]
    assert client.get(url, headers=headers).status_code == 401


def test_sharepoint_walk_and_path_rules(graph: FakeGraph) -> None:
    with sharepoint.acting_as(uuid.uuid4()):
        found = sharepoint.walk(PIECE, too_wide="demasiado")
        assert sorted(item.path for item in found) == sorted(graph.files)
        assert all((item.version or "").startswith("sp:") for item in found)
        with pytest.raises(SourceError):
            sharepoint.item("../fuera.pdf")
        with pytest.raises(SourceError) as wide:
            sharepoint.walk(PIECE, too_wide="demasiado", limit=1)
        assert wide.value.status_code == 422
    with pytest.raises(SourceError) as anonymous:
        sharepoint.item(PIECE, directory=True)
    assert anonymous.value.status_code == 401


def test_links_made_through_sharepoint_stay_readable_locally(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "a.pdf").write_bytes(b"%PDF local")
    monkeypatch.setattr(settings, "ASSETS_ROOT", str(tmp_path))
    monkeypatch.setattr(settings, "ASSETS_SOURCE_ID", f"local-{uuid.uuid4()}")
    rows = [
        StoredFile(
            filename="a.pdf",
            content_type="application/pdf",
            source="local",
            source_key=settings.ASSETS_SOURCE_ID,
            source_path="a.pdf",
            source_version=version,
            version=uuid.uuid4(),
        )
        for version in ("sp:abc:10", "1:10")
    ]
    db.add_all(rows)
    db.commit()
    headers = superuser_token_headers
    assert client.get(f"{API}/files/{rows[0].id}", headers=headers).content == (
        b"%PDF local"
    )
    # A local link keeps its change detection.
    assert client.get(f"{API}/files/{rows[1].id}", headers=headers).status_code == 409


class FakeMsal:
    claims: dict[str, Any] = {}
    modes: list[str | None] = []

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def initiate_auth_code_flow(
        self, _scopes: list[str], **kwargs: Any
    ) -> dict[str, Any]:
        self.modes.append(kwargs.get("response_mode"))
        state = uuid.uuid4().hex
        return {"state": state, "auth_uri": f"https://login.test/?state={state}"}

    def acquire_token_by_auth_code_flow(
        self, flow: dict[str, Any], response: dict[str, str]
    ) -> dict[str, Any]:
        if response.get("state") != flow["state"]:
            raise ValueError("state mismatch")
        return {"access_token": "graph", "id_token_claims": self.claims}


@pytest.fixture
def microsoft(monkeypatch: pytest.MonkeyPatch) -> type[FakeMsal]:
    monkeypatch.setattr(settings, "SHAREPOINT_ENABLED", True)
    monkeypatch.setattr(settings, "MICROSOFT_TENANT_ID", "tenant-1")
    monkeypatch.setattr(settings, "MICROSOFT_CLIENT_ID", "client-1")
    monkeypatch.setattr(settings, "MICROSOFT_CLIENT_SECRET", "secret")
    monkeypatch.setattr(
        settings, "MICROSOFT_REDIRECT_URI", "https://oauth.pstmn.io/v1/browser-callback"
    )
    monkeypatch.setattr(microsoft_auth, "application", FakeMsal)
    FakeMsal.claims = {
        "tid": "tenant-1",
        "oid": f"oid-{uuid.uuid4()}",
        "preferred_username": settings.FIRST_SUPERUSER.upper(),
    }
    FakeMsal.modes = []
    return FakeMsal


def test_login_methods_follow_the_switch(client: TestClient) -> None:
    methods = client.get(f"{API}/login/methods").json()
    assert methods["password"] and not methods["microsoft"]
    assert client.post(f"{API}/login/microsoft/start").status_code == 404


def test_microsoft_sign_in_by_pasting_the_redirect(
    client: TestClient, microsoft: type[FakeMsal]
) -> None:
    methods = client.get(f"{API}/login/methods").json()
    assert methods == {
        "password": False,
        "microsoft": True,
        "microsoft_paste": True,
        "sharepoint": True,
        "source_name": settings.ASSETS_SOURCE_NAME,
    }
    password = client.post(
        f"{API}/login/access-token",
        data={"username": settings.FIRST_SUPERUSER, "password": "irrelevant"},
    )
    assert password.status_code == 400

    auth_uri = client.post(f"{API}/login/microsoft/start").json()["auth_uri"]
    assert microsoft.modes == ["query"]
    state = parse_qs(urlsplit(auth_uri).query)["state"][0]
    pasted = f"https://oauth.pstmn.io/v1/browser-callback?code=c&state={state}"
    url = f"{API}/login/microsoft/complete"
    assert (
        client.post(
            url, json={"response_url": "https://elsewhere.test/?x=1"}
        ).status_code
        == 400
    )
    token = client.post(url, json={"response_url": pasted})
    assert token.status_code == 200, token.text
    me = client.get(
        f"{API}/users/me",
        headers={"Authorization": f"Bearer {token.json()['access_token']}"},
    ).json()
    assert me["email"] == settings.FIRST_SUPERUSER
    # Each authorization can be completed once.
    assert client.post(url, json={"response_url": pasted}).status_code == 400

    microsoft.claims = {
        **microsoft.claims,
        "oid": "other",
        "preferred_username": "x@y.z",
    }
    state = parse_qs(
        urlsplit(client.post(f"{API}/login/microsoft/start").json()["auth_uri"]).query
    )["state"][0]
    unknown = client.post(
        url,
        json={
            "response_url": f"https://oauth.pstmn.io/v1/browser-callback?state={state}&code=c"
        },
    )
    assert unknown.status_code == 400 and "no tiene acceso" in unknown.json()["detail"]


def test_microsoft_callback_hands_a_one_time_ticket(
    client: TestClient, microsoft: type[FakeMsal], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        settings,
        "MICROSOFT_REDIRECT_URI",
        f"http://localhost:8000{API}/login/microsoft/callback",
    )
    assert not client.get(f"{API}/login/methods").json()["microsoft_paste"]
    auth_uri = client.post(f"{API}/login/microsoft/start").json()["auth_uri"]
    assert microsoft.modes == ["form_post"]
    state = parse_qs(urlsplit(auth_uri).query)["state"][0]
    redirect = client.post(
        f"{API}/login/microsoft/callback",
        data={"state": state, "code": "c"},
        follow_redirects=False,
    )
    assert redirect.status_code == 303
    location = urlsplit(redirect.headers["location"])
    assert location.path == "/login"
    ticket = parse_qs(location.query)["microsoft"][0]
    url = f"{API}/login/microsoft/ticket"
    assert client.post(url, json={"ticket": ticket}).status_code == 200
    assert client.post(url, json={"ticket": ticket}).status_code == 400

    failed = client.post(
        f"{API}/login/microsoft/callback",
        data={"state": "unknown", "error": "access_denied"},
        follow_redirects=False,
    )
    assert "microsoft_error" in parse_qs(urlsplit(failed.headers["location"]).query)


def test_graph_token_requires_a_microsoft_session() -> None:
    with pytest.raises(SourceError) as error:
        microsoft_auth.access_token(uuid.uuid4())
    assert error.value.status_code == 401


def test_rebase_prefixes_paths_and_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ASSETS_SOURCE_ID", f"rebase-{uuid.uuid4()}")
    folder = f"Pieza {uuid.uuid4()}"
    prefix = f"Grupo {uuid.uuid4()}"
    with Session(engine) as session:
        part = Part(code=f"R-{uuid.uuid4().hex[:8]}", name="Rebase", folder_path=folder)
        file = StoredFile(
            filename="a.pdf",
            source="local",
            source_key=settings.ASSETS_SOURCE_ID,
            source_path=f"{folder}/a.pdf",
            source_version="1:2",
            reference_key=reference_key(f"{folder}/a.pdf", "1:2"),
        )
        session.add_all([part, file])
        session.flush()
        session.add(
            MeasurementImport(
                part_id=part.id,
                fingerprint=uuid.uuid4().hex,
                revision="01",
                sample="01",
                cavity="c1",
                source_path=folder,
                source_id=settings.ASSETS_SOURCE_ID,
                sha256="0" * 64,
                reader="test",
                rows=[],
            )
        )
        counts = rebase(session, prefix, check_root=False)
        assert counts["files"] == 1 and counts["imports"] == 1
        assert counts["unexpected_keys"] == 0
        assert part.folder_path == f"{prefix}/{folder}"
        assert file.reference_key == reference_key(f"{prefix}/{folder}/a.pdf", "1:2")
        batch = session.exec(
            select(MeasurementImport).where(MeasurementImport.part_id == part.id)
        ).one()
        assert batch.source_path == f"{prefix}/{folder}"
        with pytest.raises(RebaseError):
            rebase(session, prefix, check_root=False)
        with pytest.raises(RebaseError):
            rebase(session, "../fuera", check_root=False)
        session.rollback()


def test_pilot_is_found_under_any_root() -> None:
    assert is_pilot(Part(code="3212", name="x", folder_path=PIECE))
    assert is_pilot(Part(code="3212", name="x", folder_path="3212 Pump Housing"))
    assert not is_pilot(Part(code="3197", name="x", folder_path=PIECE))
