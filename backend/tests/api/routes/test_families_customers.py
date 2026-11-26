import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.knowledge_models import PartCharacteristic
from app.models import FeaturePartLink
from tests.utils.feature import create_random_feature, create_random_part

API = settings.API_V1_STR


@pytest.mark.parametrize("kind", ["families", "customers", "materials"])
def test_adding_an_existing_name_returns_it(
    client: TestClient, superuser_token_headers: dict[str, str], kind: str
) -> None:
    url = f"{API}/{kind}"
    token = uuid.uuid4().hex[:8]
    assert client.get(url).status_code == 401
    first = client.post(
        url, headers=superuser_token_headers, json={"name": f"Bosch {token}"}
    )
    assert first.status_code == 200, first.text
    for variant in (f"bosch {token}", f"  BOSCH   {token} ", f"Bosch {token}"):
        again = client.post(
            url, headers=superuser_token_headers, json={"name": variant}
        )
        assert again.json() == first.json()
    other = client.post(
        url, headers=superuser_token_headers, json={"name": f"Robert Bosch {token}"}
    ).json()
    assert other["id"] != first.json()["id"]
    names = [
        row["name"]
        for row in client.get(url, headers=superuser_token_headers).json()["data"]
    ]
    assert names.count(f"Bosch {token}") == 1 and f"Robert Bosch {token}" in names
    assert (
        client.post(
            url, headers=superuser_token_headers, json={"name": "   "}
        ).status_code
        == 422
    )


def test_piece_family_and_customer_are_optional_references(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    headers = superuser_token_headers
    part = create_random_part(db)
    url = f"{API}/parts/{part.id}"
    detail = client.get(f"{url}/detail", headers=headers).json()["part"]
    assert detail["family"] is None and detail["customer"] is None
    family = client.post(
        f"{API}/families", headers=headers, json={"name": f"Pot {uuid.uuid4().hex[:8]}"}
    ).json()
    assert (
        client.put(
            url, headers=headers, json={"family_id": str(uuid.uuid4())}
        ).status_code
        == 422
    )
    response = client.put(url, headers=headers, json={"family_id": family["id"]})
    assert response.status_code == 200, response.text
    assert response.json()["family"] == family
    # Omitted keeps the value; null clears it.
    assert (
        client.put(url, headers=headers, json={"name": "Renamed"}).json()["family"]
        == family
    )
    assert (
        client.put(url, headers=headers, json={"family_id": None}).json()["family"]
        is None
    )
    created = client.post(
        f"{API}/parts/",
        headers=headers,
        json={"code": uuid.uuid4().hex[:10], "family_id": family["id"]},
    )
    assert created.status_code == 200, created.text
    assert created.json()["family"] == family and created.json()["name"] is None


def test_filters_combine_family_and_customer_on_the_same_piece(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    headers = superuser_token_headers
    token = uuid.uuid4().hex[:8]

    def add(kind: str, name: str) -> str:
        return client.post(
            f"{API}/{kind}", headers=headers, json={"name": f"{name} {token}"}
        ).json()["id"]

    pump, pot = add("families", "Pump Housing"), add("families", "Pot")
    bosch, other = add("customers", "Bosch"), add("customers", "Other")
    # P1: Pump Housing of Bosch. P2: Pump Housing of another customer. P3: Bosch Pot.
    pieces = [create_random_part(db) for _ in range(3)]
    for piece, (family, customer) in zip(
        pieces, [(pump, bosch), (pump, other), (pot, bosch)], strict=True
    ):
        piece.family_id, piece.customer_id = uuid.UUID(family), uuid.UUID(customer)
        db.add(piece)
    both, split = create_random_feature(db), create_random_feature(db)
    db.add_all(
        [
            FeaturePartLink(feature_id=both.id, part_id=pieces[0].id),
            FeaturePartLink(feature_id=split.id, part_id=pieces[1].id),
            FeaturePartLink(feature_id=split.id, part_id=pieces[2].id),
            PartCharacteristic(part_id=pieces[0].id, code="N901", revision="01"),
            PartCharacteristic(part_id=pieces[1].id, code="N901", revision="01"),
        ]
    )
    db.commit()

    def catalog(**params: str) -> tuple[set[str], set[str], set[str]]:
        data = client.get(f"{API}/catalog", headers=headers, params=params).json()
        return (
            {p["id"] for p in data["parts"]},
            {f["id"] for f in data["features"]},
            {c["part"]["id"] for c in data["cotas"]},
        )

    p1, p2, p3 = (str(p.id) for p in pieces)
    parts, features, _ = catalog(family_id=pump, customer_id=bosch)
    assert parts == {p1}
    # `split` has a Pump Housing and a Bosch piece, but not one that is both.
    assert not features
    assert catalog(family_id=pump, customer_id=bosch, kind="feature")[1] == {
        str(both.id)
    }
    parts, features, _ = catalog(family_id=pump)
    assert parts == {p1, p2} and features == {str(both.id), str(split.id)}
    parts, features, _ = catalog(customer_id=other)
    assert parts == {p2} and not features
    assert catalog(family_id=pot, customer_id=other)[:2] == (set(), set())
    _, _, cotas = catalog(q="N901", family_id=pump, customer_id=bosch)
    assert cotas == {p1}
    data = client.get(
        f"{API}/catalog",
        headers=headers,
        params={"family_id": pump, "customer_id": bosch},
    ).json()
    assert data["parts"][0]["family"]["id"] == pump
    assert data["parts"][0]["customer"]["id"] == bosch
