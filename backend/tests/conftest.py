from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.core.config import settings
from app.core.db import engine, init_db
from app.main import app
from app.models import Feature, Item, Part, StoredFile, User
from tests.utils.user import authentication_token_from_email
from tests.utils.utils import get_superuser_token_headers


def pytest_configure() -> None:
    # Run before collection/fixtures, including when pytest is called directly.
    if not settings.POSTGRES_DB.endswith("_test"):
        raise pytest.UsageError(
            "Refusing destructive tests: POSTGRES_DB must end in '_test'. "
            "Use scripts/test.sh or scripts/test.ps1 for an isolated stack."
        )


@pytest.fixture(scope="session", autouse=True)
def db(tmp_path_factory: pytest.TempPathFactory) -> Generator[Session, None, None]:
    # File deletion tests must never use application uploads, even with a test DB.
    original_uploads = settings.UPLOADS_DIR
    settings.UPLOADS_DIR = str(tmp_path_factory.mktemp("uploads"))
    with Session(engine) as session:
        init_db(session)
        yield session
        statement = delete(Item)
        session.execute(statement)
        # Las notas, los adjuntos y los enlaces a piezas caen por CASCADE
        statement = delete(Feature)
        session.execute(statement)
        statement = delete(Part)
        session.execute(statement)
        statement = delete(StoredFile)
        session.execute(statement)
        statement = delete(User)
        session.execute(statement)
        session.commit()
    settings.UPLOADS_DIR = original_uploads


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
