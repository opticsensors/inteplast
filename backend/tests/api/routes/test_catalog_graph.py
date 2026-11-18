import uuid
from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import FeaturePartLink
from tests.utils.feature import create_random_feature, create_random_part

API = settings.API_V1_STR


def _catalog(
    db: Session, client: TestClient, headers: dict[str, str]
) -> dict[str, Any]:
    """P1: Pump Housing of Bosch. P2: Pump Housing of another customer. P3: Bosch Pot."""
    token = uuid.uuid4().hex[:8]

    def add(kind: str, name: str) -> str:
        return str(
            client.post(
                f"{API}/{kind}", headers=headers, json={"name": f"{name} {token}"}
            ).json()["id"]
        )

    ids = {
        "pump": add("families", "Pump Housing"),
        "pot": add("families", "Pot"),
        "bosch": add("customers", "Bosch"),
        "other": add("customers", "Other"),
    }
    pieces = [create_random_part(db) for _ in range(3)]
    for piece, (family, customer) in zip(
        pieces,
        [("pump", "bosch"), ("pump", "other"), ("pot", "bosch")],
        strict=True,
    ):
        piece.family_id = uuid.UUID(ids[family])
        piece.customer_id = uuid.UUID(ids[customer])
        piece.name = f"Housing {token}"
        db.add(piece)
    both, split = create_random_feature(db), create_random_feature(db)
    both.name, split.name = f"Both {token}", f"Split {token}"
    db.add_all(
        [
            both,
            split,
            FeaturePartLink(feature_id=both.id, part_id=pieces[0].id),
            FeaturePartLink(feature_id=split.id, part_id=pieces[1].id),
            FeaturePartLink(feature_id=split.id, part_id=pieces[2].id),
        ]
    )
    db.commit()
    ids.update(
        {f"p{i + 1}": str(piece.id) for i, piece in enumerate(pieces)},
        both=str(both.id),
        split=str(split.id),
        token=token,
    )
    return ids


def _graph(client: TestClient, headers: dict[str, str], **params: Any) -> Any:
    response = client.get(f"{API}/catalog/graph", headers=headers, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def _by_kind(graph: dict[str, Any]) -> dict[str, set[str]]:
    kinds: dict[str, set[str]] = {}
    for node in graph["nodes"]:
        kinds.setdefault(node["kind"], set()).add(node["ref_id"])
    return kinds


def test_graph_nodes_and_links_follow_the_catalogue_filters(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    headers = superuser_token_headers
    ids = _catalog(db, client, headers)
    assert client.get(f"{API}/catalog/graph").status_code == 401
    graph = _graph(client, headers, family_id=ids["pump"], customer_id=ids["bosch"])
    assert _by_kind(graph) == {
        "part": {ids["p1"]},
        "feature": {ids["both"]},
        "family": {ids["pump"]},
        "customer": {ids["bosch"]},
    }
    p1 = f"part:{ids['p1']}"
    assert {
        (link["source"], link["target"], link["kind"]) for link in graph["links"]
    } == {
        (p1, f"feature:{ids['both']}", "feature"),
        (p1, f"family:{ids['pump']}", "family"),
        (p1, f"customer:{ids['bosch']}", "customer"),
    }
    assert graph["total"] == 4 and graph["truncated"] is False
    piece = next(node for node in graph["nodes"] if node["kind"] == "part")
    assert piece["name"] == f"Housing {ids['token']}" and piece["image"] is None
    # With a family only, the feature split between two pieces appears too.
    graph = _graph(client, headers, family_id=ids["pump"])
    kinds = _by_kind(graph)
    assert kinds["part"] == {ids["p1"], ids["p2"]}
    assert kinds["feature"] == {ids["both"], ids["split"]}
    assert kinds["customer"] == {ids["bosch"], ids["other"]}
    # Pieces only: no feature nodes and no feature links.
    graph = _graph(client, headers, family_id=ids["pump"], kind="part")
    assert "feature" not in _by_kind(graph)
    assert all(link["kind"] != "feature" for link in graph["links"])


def test_graph_shows_the_same_pieces_and_features_as_the_list(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    headers = superuser_token_headers
    ids = _catalog(db, client, headers)
    for params in (
        {"family_id": ids["pump"]},
        {"customer_id": ids["bosch"]},
        {"family_id": ids["pump"], "customer_id": ids["bosch"]},
        {"family_id": ids["pot"], "customer_id": ids["other"]},
        {"q": ids["token"]},
        {"q": ids["token"], "feature_id": ids["split"]},
        {"q": ids["token"], "part_id": ids["p3"]},
    ):
        listed = client.get(
            f"{API}/catalog", headers=headers, params={**params, "limit": 100}
        ).json()
        kinds = _by_kind(_graph(client, headers, **params))
        assert kinds.get("part", set()) == {p["id"] for p in listed["parts"]}, params
        assert kinds.get("feature", set()) == {f["id"] for f in listed["features"]}, (
            params
        )


def test_graph_says_when_it_is_cut_and_gives_the_real_total(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    headers = superuser_token_headers
    ids = _catalog(db, client, headers)
    whole = _graph(client, headers, family_id=ids["pump"])
    assert whole["total"] == 7 and not whole["truncated"]
    cut = _graph(client, headers, family_id=ids["pump"], limit=3)
    assert cut["total"] == 7 and cut["truncated"] is True
    assert len(cut["nodes"]) == 3
    shown = {node["id"] for node in cut["nodes"]}
    # Links never point at a node that was left out.
    assert all(
        link["source"] in shown and link["target"] in shown for link in cut["links"]
    )
    assert (
        client.get(
            f"{API}/catalog/graph", headers=headers, params={"limit": 501}
        ).status_code
        == 422
    )
