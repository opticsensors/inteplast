import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlmodel import Session, func, select

from app.core.config import Settings, settings
from app.core.security import ALGORITHM
from app.models import Part
from tests.utils.feature import (
    create_random_asset,
    create_random_feature,
    create_random_note,
    create_random_part,
)
from tests.utils.user import create_random_user
from tests.utils.utils import random_email


def test_signup_disabled_by_default(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert Settings.model_fields["ALLOW_PUBLIC_SIGNUP"].default is False
    monkeypatch.setattr(settings, "ALLOW_PUBLIC_SIGNUP", False)
    response = client.post(
        f"{settings.API_V1_STR}/users/signup",
        json={"email": random_email(), "password": "valid-test-password"},
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    ("environment", "database"), [("local", "app"), ("production", "app_test")]
)
def test_test_routes_require_isolated_local_database(
    environment: str, database: str
) -> None:
    values = settings.model_dump(exclude={"SQLALCHEMY_DATABASE_URI", "uploads_path"})
    values.update(
        ENABLE_TEST_ROUTES=True,
        ENVIRONMENT=environment,
        POSTGRES_DB=database,
        SECRET_KEY="test-secret-not-default",
        POSTGRES_PASSWORD="test-password-not-default",
        FIRST_SUPERUSER_PASSWORD="test-password-not-default",
    )
    with pytest.raises(ValidationError, match="Test routes require"):
        Settings(**values)


@pytest.mark.parametrize(
    ("resource", "field"),
    [
        ("feature", "name"),
        ("feature", "tags"),
        ("note", "title"),
        ("note", "kind"),
        ("note", "position"),
        ("asset", "name"),
        ("asset", "kind"),
        ("asset", "position"),
        ("part", "code"),
    ],
)
def test_nonnullable_update_rejected_before_database(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
    resource: str,
    field: str,
) -> None:
    feature = create_random_feature(db)
    paths = {
        "feature": f"/features/{feature.id}",
        "note": f"/features/notes/{create_random_note(db, feature).id}",
        "asset": f"/features/assets/{create_random_asset(db, feature).id}",
        "part": f"/parts/{create_random_part(db).id}",
    }
    response = client.put(
        settings.API_V1_STR + paths[resource],
        headers=superuser_token_headers,
        json={field: None},
    )
    assert response.status_code == 422
    # A validation failure must not poison later requests or erase the feature.
    assert (
        client.get(
            f"{settings.API_V1_STR}/features/{feature.id}",
            headers=superuser_token_headers,
        ).status_code
        == 200
    )


def test_nullable_note_body_can_be_cleared(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    note = create_random_note(db, create_random_feature(db))
    response = client.put(
        f"{settings.API_V1_STR}/features/notes/{note.id}",
        headers=superuser_token_headers,
        json={"body": None},
    )
    assert response.status_code == 200
    assert response.json()["body"] is None
    assert response.json()["title"] == note.title


def test_missing_file_references_return_404(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    feature = create_random_feature(db)
    asset = create_random_asset(db, feature)
    missing = str(uuid.uuid4())
    cases = [
        ("post", "/features/", {"name": "Missing image", "image_id": missing}),
        ("put", f"/features/{feature.id}", {"image_id": missing}),
        (
            "post",
            f"/features/{feature.id}/assets",
            {"kind": "part", "name": "Missing file", "file_id": missing},
        ),
        ("put", f"/features/assets/{asset.id}", {"file_id": missing}),
    ]
    for method, path, payload in cases:
        response = client.request(
            method,
            settings.API_V1_STR + path,
            headers=superuser_token_headers,
            json=payload,
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "File not found"


def test_parts_count_is_total_across_pages(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    create_random_part(db)
    create_random_part(db)
    total = db.exec(select(func.count()).select_from(Part)).one()
    response = client.get(
        f"{settings.API_V1_STR}/parts/",
        headers=superuser_token_headers,
        params={"skip": 1, "limit": 1},
    )
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1
    assert response.json()["count"] == total


def test_file_links_are_scoped_expiring_and_not_api_credentials(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    upload = client.post(
        f"{settings.API_V1_STR}/files/",
        headers=superuser_token_headers,
        files={"file": ("example.pdf", b"%PDF-test", "application/pdf")},
    )
    assert upload.status_code == 200
    file_id = upload.json()["id"]
    path = f"{settings.API_V1_STR}/files/{file_id}"
    assert client.get(path).status_code == 401
    assert client.get(path + "/access-url").status_code == 401
    assert client.get(path, headers=superuser_token_headers).status_code == 200
    link = client.get(path + "/access-url", headers=superuser_token_headers)
    assert link.status_code == 200
    url = link.json()["url"]
    response = client.get(url)
    assert response.status_code == 200
    assert response.content == b"%PDF-test"
    assert response.headers["content-disposition"].startswith("inline;")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "private, no-store"
    token = parse_qs(urlsplit(url).query)["token"][0]
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["purpose"] == "file-access"
    assert (
        client.get(
            f"{settings.API_V1_STR}/files/{uuid.uuid4()}", params={"token": token}
        ).status_code
        == 401
    )
    assert (
        client.get(
            f"{settings.API_V1_STR}/users/me",
            headers={"Authorization": f"Bearer {token}"},
        ).status_code
        == 403
    )
    payload["exp"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    expired = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)
    assert client.get(path, params={"token": expired}).status_code == 401
    assert client.get(path, params={"token": "invalid"}).status_code == 401
    assert (
        client.get(url + "&download=true")
        .headers["content-disposition"]
        .startswith("attachment;")
    )


@pytest.mark.parametrize("removed", [False, True])
def test_file_link_stops_working_when_user_disabled_or_deleted(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
    removed: bool,
) -> None:
    user = create_random_user(db)
    upload = client.post(
        f"{settings.API_V1_STR}/files/",
        headers=superuser_token_headers,
        files={"file": ("example.txt", b"example", "text/plain")},
    )
    file_id = upload.json()["id"]
    token = jwt.encode(
        {
            "sub": file_id,
            "uid": str(user.id),
            "purpose": "file-access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=1),
        },
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    path = f"{settings.API_V1_STR}/files/{file_id}"
    assert client.get(path, params={"token": token}).status_code == 200
    if removed:
        db.delete(user)
    else:
        user.is_active = False
        db.add(user)
    db.commit()
    assert client.get(path, params={"token": token}).status_code == 401


@pytest.mark.parametrize("content_type", ["text/html", "image/svg+xml"])
def test_active_uploads_are_served_as_attachments(
    client: TestClient, superuser_token_headers: dict[str, str], content_type: str
) -> None:
    upload = client.post(
        f"{settings.API_V1_STR}/files/",
        headers=superuser_token_headers,
        files={"file": ("active.html", b"<script>alert(1)</script>", content_type)},
    )
    response = client.get(
        f"{settings.API_V1_STR}/files/{upload.json()['id']}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["content-disposition"].startswith("attachment;")
    assert response.headers["x-content-type-options"] == "nosniff"
