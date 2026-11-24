import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app import sharepoint
from app.api.routes.originals import (
    catalog_part_folders,
    sample_part_folders,
    sharing_url,
)
from app.core.config import settings
from app.microsoft_models import MicrosoftAccount, SharePointFolder
from app.models import Part, StoredFile
from app.source_types import SourceError

API = f"{settings.API_V1_STR}/admin/originals"


def test_library_browser_link() -> None:
    assert (
        sharing_url(
            "https://org.sharepoint.com/sites/p/Forms/AllItems.aspx?id=%2Fsites%2Fp%2FData%2FMy%20Folder"
        )
        == "https://org.sharepoint.com/sites/p/Data/My%20Folder"
    )


def test_sample_prefers_different_feature_folders() -> None:
    paths = ["A/P1", "A/P2", "A/P3", "B/Tipo A/P4", "C/P5", "D/P6"]
    assert sample_part_folders(paths) == ["A/P1", "B/Tipo A/P4", "C/P5"]
    assert sample_part_folders(paths[:4]) == ["A/P1", "B/Tipo A/P4", "A/P2"]
    assert sample_part_folders(paths[:2]) == paths[:2]
    assert sample_part_folders([]) == []


def test_change_originals(
    client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    superuser_token_headers: dict[str, str],
    normal_user_token_headers: dict[str, str],
) -> None:
    headers = superuser_token_headers
    source = f"originals-{uuid.uuid4()}"
    monkeypatch.setattr(settings, "ASSETS_SOURCE_ID", source)
    monkeypatch.setattr(settings, "SHAREPOINT_ENABLED", True)
    uid = uuid.UUID(
        client.get(f"{settings.API_V1_STR}/users/me", headers=headers).json()["id"]
    )
    account = MicrosoftAccount(
        user_id=uid,
        object_id=str(uuid.uuid4()),
        tenant_id="tenant",
        username="admin@example.com",
        token_cache="test",
    )
    # Existing Microsoft sign-in tests may also bind this test administrator.
    saved_account = db.get(MicrosoftAccount, uid)
    tenant = saved_account.tenant_id if saved_account else account.tenant_id
    if not saved_account:
        db.add(account)
    for feature in ("A", "B"):
        code = uuid.uuid4().hex
        db.add(Part(code=code, folder_path=f"{feature}/{code}"))
    db.commit()
    paths = catalog_part_folders(db)
    sample = sample_part_folders(paths)
    absent = sample[-1]
    checked_paths: list[str] = []
    item = "root-A"
    org = tenant
    deny = False

    def graph(
        url: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        assert sharepoint.acting_user.get() == uid
        if url.endswith(":"):
            for path in sample:
                if url == sharepoint.folder_item_url("library", item, path):
                    assert params == {"$select": "folder"}
                    checked_paths.append(path)
                    if path == absent:
                        raise SourceError("missing", "No encontrado", 404)
                    return {"folder": {}}
            pytest.fail(f"Unexpected lookup outside the piece folder sample: {url}")
        if url.endswith("/children"):
            assert ":/" not in url.removeprefix(sharepoint.GRAPH)
            if deny:
                raise SourceError("unavailable", "Sin acceso", 409)
            return {"value": []}
        if "/shares/" in url or "/items/" in url:
            folder = item if "/shares/" in url else url.rsplit("/", 1)[-1]
            return {
                "id": folder,
                "folder": {},
                "parentReference": {"driveId": "library"},
                "name": folder,
                "sharepointIds": {"tenantId": org},
                "webUrl": "https://org.sharepoint.com/" + folder,
            }
        return {
            "folder": {},
            "id": "old",
            "name": "old",
            "webUrl": "https://org.sharepoint.com/old",
        }

    monkeypatch.setattr(sharepoint, "request", graph)
    link = {"url": "https://org.sharepoint.com/sites/project/folder"}
    assert (
        client.post(
            API + "/check", headers=normal_user_token_headers, json=link
        ).status_code
        == 403
    )
    assert (
        client.put(
            API, headers=normal_user_token_headers, json={"ticket": "invalid"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            API + "/check", headers=headers, json={"url": "https://example.org/x"}
        ).status_code
        == 422
    )
    org = "another-tenant"
    assert client.post(API + "/check", headers=headers, json=link).status_code == 422
    org = tenant
    deny = True
    assert client.post(API + "/check", headers=headers, json=link).status_code == 409
    deny = False
    checked = client.post(API + "/check", headers=headers, json=link)
    assert checked.status_code == 200, checked.text
    result = checked.json()
    assert checked_paths == sample
    assert result["checked"] == len(sample)
    assert (result["found"], result["total"], result["unavailable"]) == (
        len(sample) - 1,
        len(paths),
        [absent],
    )
    # The relative path saved for an old Excel is absent after reorganizing
    # Metrology. Folder validation must still return the same result.
    db.add(
        StoredFile(
            source="local",
            source_key=source,
            source_path=f"{sample[0]}/Metrologia/old.xls",
            filename="old.xls",
        )
    )
    db.commit()
    checked_paths.clear()
    again = client.post(API + "/check", headers=headers, json=link).json()
    assert (again["found"], again["unavailable"]) == (result["found"], [absent])
    assert checked_paths == sample
    assert db.get(SharePointFolder, source) is None
    first = {"ticket": result["ticket"]}
    item = "root-B"
    competing = {
        "ticket": client.post(API + "/check", headers=headers, json=link).json()[
            "ticket"
        ]
    }
    assert (
        client.put(API, headers=headers, json={"ticket": "invalid"}).status_code == 422
    )
    assert client.put(API, headers=headers, json=first).status_code == 200
    assert client.put(API, headers=headers, json=competing).status_code == 409
    assert client.get(API, headers=headers).json()["name"] == "root-A"
    assert client.put(API, headers=headers, json=first).status_code == 200
    next_check = client.post(API + "/check", headers=headers, json=link).json()
    assert (
        client.put(
            API, headers=headers, json={"ticket": next_check["ticket"]}
        ).status_code
        == 200
    )
    with sharepoint.acting_as(uid):
        assert sharepoint.item_url("x/a.pdf").endswith("/items/root-B:/x/a.pdf:")
        payload = {
            "id": "file1",
            "size": 1,
            "cTag": "v1",
            "parentReference": {"driveId": "library"},
        }
        assert sharepoint.version(payload) != sharepoint.version(
            {**payload, "id": "file2"}
        )
    if not saved_account:
        db.delete(account)
        db.commit()
