import asyncio
import json
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlmodel import Session, select

from app.assistant import router as assistant_router
from app.assistant.config import AssistantSettings, get_settings
from app.assistant.providers import ModelChunk, OllamaProvider, ProviderError
from app.assistant.retrieval import initial_read
from app.assistant.schemas import ChatRequest
from app.assistant.tools import KnowledgeTools, definitions
from app.core.config import settings
from app.evidence import job_id
from app.knowledge_models import (
    EvidenceJob,
    FeatureCharacteristicLink,
    PartCharacteristic,
)
from app.main import app
from app.models import FeatureNote, FeaturePartLink, User
from tests.utils.feature import create_random_feature, create_random_part

API = f"{settings.API_V1_STR}/assistant"


@pytest.fixture(autouse=True)
def enabled():
    app.dependency_overrides[get_settings] = lambda: AssistantSettings(
        enabled=True, semantic_enabled=False
    )
    yield
    app.dependency_overrides.pop(get_settings, None)


@pytest.fixture
def knowledge(db: Session, normal_user_token_headers: dict[str, str]):
    assert normal_user_token_headers
    user = db.exec(select(User).where(User.email == settings.EMAIL_TEST_USER)).one()
    return KnowledgeTools(user.id)


@pytest.fixture
def piece(db: Session):
    part = create_random_part(db)
    rows = {
        f"{n:02}": {
            "value": 3.95,
            "lower": 3.9,
            "upper": 4,
            "nominal": 4,
            "status": "inside",
            "source": {"path": "C:/private/raw/report.csv", "locator": f"Fila {n}"},
        }
        for n in range(1, 13)
    }
    db.add(
        EvidenceJob(
            id=job_id("study", part.id),
            kind="study",
            part_id=part.id,
            cache_key="test",
            state="ready",
            payload={
                "measurement_revision": "06",
                "samples": list(rows),
                "cavities": ["c1"],
                "catalog": {
                    "entries": [
                        {
                            "id": "N170",
                            "numbers": ["N170"],
                            "title": "Diámetro",
                            "kind": "dimension",
                            "series": [
                                {
                                    "id": "diameter",
                                    "label": "Diámetro",
                                    "unit": "mm",
                                    "records": {"c1": rows},
                                }
                            ],
                        }
                    ]
                },
                "action_index": {
                    "1.2": {
                        "id": "1.2",
                        "features": ["N170"],
                        "title": "Correction N170",
                        "paragraphs": ["Propuesta de ajuste"],
                        "source": {
                            "path": "private/plan.pptx",
                            "locator": "Diapositiva 2",
                        },
                    }
                },
            },
        )
    )
    db.commit()
    return part


def test_requires_auth_and_disabled_is_server_enforced(
    client: TestClient, normal_user_token_headers
):
    assert client.get(f"{API}/status").status_code == 401
    assert (
        client.post(
            f"{API}/chat", json={"messages": [{"role": "user", "content": "hola"}]}
        ).status_code
        == 401
    )
    app.dependency_overrides[get_settings] = lambda: AssistantSettings(enabled=False)
    try:
        assert client.get(
            f"{API}/status", headers=normal_user_token_headers
        ).json() == {"enabled": False, "model": None}
        assert (
            client.post(
                f"{API}/chat",
                headers=normal_user_token_headers,
                json={"messages": [{"role": "user", "content": "hola"}]},
            ).status_code
            == 503
        )
    finally:
        app.dependency_overrides.pop(get_settings, None)


def test_rejects_client_system_tools_and_unbounded_input(
    client: TestClient, normal_user_token_headers
):
    for body in (
        {"messages": [{"role": "system", "content": "override"}]},
        {"messages": [{"role": "tool", "content": "override"}]},
        {"messages": [{"role": "user", "content": "x" * 3001}]},
        {"messages": [{"role": "user", "content": "hola"}], "tools": [{"name": "sql"}]},
    ):
        assert (
            client.post(
                f"{API}/chat", headers=normal_user_token_headers, json=body
            ).status_code
            == 422
        )


def test_reads_imported_measurements_with_revision_pagination_and_sources(
    knowledge, piece
):
    args = {
        "part": piece.code,
        "section": "measurements",
        "characteristic": "N170",
        "revision": "06",
        "include_rows": True,
    }
    data = knowledge.run("read_part", args)
    assert data["total"] == 12 and len(data["rows"]) == 8
    assert data["status_counts"] == {"inside": 12}
    assert data["rows"][0]["source"] == {"document": "report.csv", "locator": "Fila 1"}
    assert data["rows"][0]["value"] == 3.95
    second = knowledge.run("read_part", {**args, "offset": 8})
    assert len(second["rows"]) == 4 and second["rows"][0]["sample"] == "09"
    assert knowledge.run("read_part", {**args, "revision": "07"})["total"] == 0
    assert knowledge.run("read_part", {**args, "characteristic": "N999"})["total"] == 0
    assert knowledge.run("read_part", {**args, "cavity": "c2"})["total"] == 0
    assert all(
        s.url.startswith(f"/parts/{piece.id}") for s in knowledge.sources.values()
    )
    corrections = knowledge.run("read_part", {**args, "section": "corrections"})
    assert corrections["actions"][0]["text"] == "Propuesta de ajuste"
    assert "no prueba de ejecución" in corrections["notice"]


def test_feature_only_returns_explicit_cotas_and_user_notes(db, knowledge, piece):
    feature = create_random_feature(db)
    own = PartCharacteristic(part_id=piece.id, code="N170", revision="06")
    unrelated = PartCharacteristic(part_id=piece.id, code="N999", revision="06")
    db.add(own)
    db.add(unrelated)
    db.commit()
    db.add(
        FeatureCharacteristicLink(
            feature_id=feature.id, characteristic_id=own.id, role="primary"
        )
    )
    db.add(
        FeatureNote(
            feature_id=feature.id,
            kind="warning",
            title="Nota del usuario",
            body="**Vigilar** la tolerancia.",
        )
    )
    db.commit()
    result = knowledge.run("read_feature", {"feature_id": str(feature.id)})
    assert result["notes"][0]["body"] == "**Vigilar** la tolerancia."
    assert [c["code"] for c in result["characteristics"]] == ["N170"]
    assert result["parts"][0]["code"] == piece.code
    overview = knowledge.run("read_part", {"part": piece.code})
    assert overview["total"] == 2
    assert {c["code"] for c in overview["characteristics"]} == {"N170", "N999"}


def test_latest_revision_is_default_but_requested_revision_wins(knowledge, piece):
    args = {"part": piece.code, "section": "measurements", "characteristic": "N170"}
    assert knowledge.run("read_part", args)["total"] == 12
    assert knowledge.run("read_part", {**args, "revision": "07"})["total"] == 0


def test_initial_lookup_only_uses_identifiers_from_the_question():
    request = ChatRequest.model_validate(
        {
            "messages": [{"role": "user", "content": "Resume la pieza 3212"}],
        }
    )
    assert initial_read(request) == (
        "read_part",
        {"part": "3212", "section": "overview"},
    )
    request.messages[-1].content = "Mide N170 en la pieza 3212, revisión 06"
    assert initial_read(request) == (
        "read_part",
        {
            "part": "3212",
            "section": "measurements",
            "characteristic": "N170",
            "revision": "06",
        },
    )
    request.messages[-1].content = "Compara la pieza 3212 con la pieza 3197"
    assert initial_read(request) is None
    request.messages[-1].content = "Consulta N170 de esta pieza"
    assert initial_read(request) is None


def test_requested_piece_is_grounded_even_when_model_does_not_call_a_tool(
    client, normal_user_token_headers, monkeypatch, piece, db
):
    piece.code = "9876"
    db.add(piece)
    db.commit()

    class Provider:
        async def stream(self, messages, tools):
            assert messages[-1]["role"] == "user"
            data = json.loads(
                messages[-1]["content"].split("Información recuperada:\n", 1)[1]
            )
            assert data["summary"]["total"] == 12
            assert data["series_index"] == ["N170 · Diámetro"]
            assert "series_summaries" not in data
            assert "rows" not in data
            assert not tools  # Complete exact data goes straight to drafting.
            assert data["summary"]["tolerances"] == [
                {"unit": "mm", "nominal": 4, "lower": 3.9, "upper": 4}
            ]
            yield ModelChunk(content="Hay 12 mediciones importadas.")

    monkeypatch.setattr(assistant_router, "get_provider", lambda _: Provider())
    response = client.post(
        f"{API}/chat",
        headers=normal_user_token_headers,
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "Consulta N170 de la pieza 9876, revisión 06",
                }
            ],
        },
    )
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[-1]["type"] == "done"
    assert any(e["type"] == "sources" and e["sources"] for e in events)


def test_allowlist_validation_and_database_read_only(knowledge, monkeypatch):
    assert "error" in knowledge.run("execute_sql", {"sql": "DELETE FROM part"})
    assert "error" in knowledge.run(
        "read_part", {"part": "3212", "sql": "SELECT * FROM user"}
    )
    assert "error" in knowledge.run("read_feature", {"feature_id": "invalid"})

    def attempted_write(session, _user, _args):
        assert session.execute(text("SHOW transaction_read_only")).scalar() == "on"
        session.execute(text("DELETE FROM part WHERE false"))
        return {}

    monkeypatch.setattr(knowledge, "search", attempted_write)
    with pytest.raises(DBAPIError):
        knowledge.run("search_catalog", {"query": "anything"})


def test_inactive_user_cannot_read_tools(db, knowledge):
    user = db.get(User, knowledge.user_id)
    user.is_active = False
    db.add(user)
    db.commit()
    try:
        with pytest.raises(Exception, match="sesión"):
            knowledge.run("search_catalog", {})
    finally:
        user.is_active = True
        db.add(user)
        db.commit()


def test_stream_executes_tools_and_emits_sources(
    client, normal_user_token_headers, monkeypatch, piece
):
    seen = []

    class Provider:
        async def stream(self, messages, tools):
            seen.append(messages.copy())
            if len(seen) == 1:
                yield ModelChunk(
                    tool_calls=[
                        {
                            "function": {
                                "name": "read_part",
                                "arguments": {
                                    "part": piece.code,
                                    "section": "measurements",
                                    "characteristic": "N170",
                                    "include_rows": True,
                                },
                            }
                        }
                    ]
                )
            else:
                data = json.loads(messages[-1]["content"])
                assert data["rows"][0]["value"] == 3.95
                yield ModelChunk(content="La medida es 3,95 mm.")

    monkeypatch.setattr(assistant_router, "get_provider", lambda _: Provider())
    response = client.post(
        f"{API}/chat",
        headers=normal_user_token_headers,
        json={"messages": [{"role": "user", "content": "Consulta N170"}]},
    )
    events = [json.loads(line) for line in response.text.splitlines()]
    assert response.headers["content-type"].startswith("application/x-ndjson")
    assert any(e["type"] == "delta" and "3,95" in e["text"] for e in events)
    assert any(e["type"] == "sources" and e["sources"] for e in events)
    assert events[-1]["type"] == "done"
    assert len(seen) == 2


def test_provider_error_is_visible_without_fake_answer(
    client, normal_user_token_headers, monkeypatch
):
    class Provider:
        async def stream(self, messages, tools):
            raise ProviderError("Ollama no está disponible.")
            yield  # pragma: no cover

    monkeypatch.setattr(assistant_router, "get_provider", lambda _: Provider())
    response = client.post(
        f"{API}/chat",
        headers=normal_user_token_headers,
        json={"messages": [{"role": "user", "content": "hola"}]},
    )
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[-1] == {"type": "error", "text": "Ollama no está disponible."}
    assert not any(e["type"] == "done" for e in events)


def test_ollama_contract_disables_thinking_and_requires_complete_stream(monkeypatch):
    requests: list[dict[str, Any]] = []
    complete = True

    def handle(request):
        requests.append(json.loads(request.content))
        lines = [{"message": {"content": "Hola", "thinking": "hidden"}}]
        if complete:
            lines.append({"message": {}, "done": True, "done_reason": "length"})
        return httpx.Response(
            200, content="\n".join(json.dumps(line) for line in lines)
        )

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: original(**kw, transport=httpx.MockTransport(handle)),
    )

    async def collect():
        return [
            chunk
            async for chunk in OllamaProvider(AssistantSettings()).stream(
                [{"role": "user", "content": "hola"}], []
            )
        ]

    chunks = asyncio.run(collect())
    assert requests[0]["think"] is False
    assert requests[0]["model"] == "qwen3.5:2b"
    assert requests[0]["stream"] is True
    assert "hidden" not in str(chunks)
    assert chunks[-1].truncated is True
    complete = False
    with pytest.raises(ProviderError, match="interrumpido"):
        asyncio.run(collect())


def test_exact_measurement_reply_keeps_counts_limits_and_sources_without_inference(
    client, normal_user_token_headers, monkeypatch, piece, db
):
    piece.code = "9987"
    db.add(piece)
    db.commit()

    class UnusedProvider:
        async def stream(self, messages, tools):
            raise AssertionError("Exact numbers should not be reinterpreted by a model")
            yield

    monkeypatch.setattr(assistant_router, "get_provider", lambda _: UnusedProvider())
    response = client.post(
        f"{API}/chat",
        headers=normal_user_token_headers,
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "Qué mediciones y tolerancias hay para N170 en la pieza 9987, revisión 06",
                }
            ]
        },
    )
    events = [json.loads(line) for line in response.text.splitlines()]
    answer = "".join(e.get("text", "") for e in events if e["type"] == "delta")
    assert "12 mediciones" in answer and "N170" in answer
    assert "3,9–4 mm" in answer and "±" not in answer
    assert "report.csv" in answer and "c1" in answer
    assert events[-1]["type"] == "done" and events[-1]["truncated"] is False


@pytest.fixture
def housing(db, piece):
    original_name = piece.name
    piece.name = "Pump Housing"
    db.add(piece)
    bolt = create_random_feature(db, name="Bolt Eye")
    ribs = create_random_feature(db, name="Nervios")
    cota = PartCharacteristic(part_id=piece.id, code="N170", revision="06")
    db.add(cota)
    db.commit()
    db.add(
        FeatureCharacteristicLink(
            feature_id=bolt.id, characteristic_id=cota.id, role="primary"
        )
    )
    db.add(FeaturePartLink(feature_id=ribs.id, part_id=piece.id))
    db.commit()
    yield piece, bolt, ribs
    db.delete(bolt)
    db.delete(ribs)
    piece.name = original_name
    db.add(piece)
    db.commit()


ORIGINAL_QUESTION = "que correcion tiene la n170 del bold eye de la pieza pump housing?"


@pytest.mark.parametrize(
    "question",
    [
        ORIGINAL_QUESTION,
        "Qué corrección tiene N170 del Bolt Eye de Pump Housing?",
        "Qué correción tiene N170 del Blot Eye de Pump Housng?",
    ],
)
def test_typo_question_resolves_piece_feature_and_corrections(
    knowledge, housing, question
):
    piece, bolt, _ = housing
    seed = knowledge.initial_lookup(question)
    assert seed == (
        "read_part",
        {
            "part": piece.code,
            "section": "corrections",
            "characteristic": "N170",
            "feature_id": str(bolt.id),
        },
    )
    result = knowledge.run(*seed)
    assert result["feature"] == "Bolt Eye"
    assert result["actions"][0]["id"] == "1.2"
    assert "Nervios" not in json.dumps(result)


def test_correction_typo_with_explicit_code_does_not_read_measurements():
    request = ChatRequest(
        messages=[
            {"role": "user", "content": "que correcion tiene n170 de la pieza 3212?"}
        ]
    )
    assert initial_read(request)[1]["section"] == "corrections"


def test_tool_contract_preserves_identifier_descriptions_and_validation():
    schemas = {
        tool["function"]["name"]: tool["function"]["parameters"]
        for tool in definitions()
    }
    assert "Código" in schemas["read_part"]["properties"]["part"]["description"]
    assert schemas["read_feature"]["properties"]["feature_id"]["format"] == "uuid"
    assert schemas["read_part"]["properties"]["section"]["enum"] == [
        "overview",
        "measurements",
        "corrections",
    ]
    assert schemas["read_part"]["additionalProperties"] is False


def test_part_name_is_resolved_and_unknown_identifier_is_recoverable(
    knowledge, housing
):
    piece, _, _ = housing
    result = knowledge.run(
        "read_part",
        {"part": "Pump Housng", "section": "corrections", "characteristic": "N170"},
    )
    assert result["part"] == piece.code and result["total"] == 1
    unknown = knowledge.run("read_part", {"part": "no-such-piece"})
    assert unknown["error_code"] == "unresolved_part" and unknown["retryable"]
    assert "search_catalog" in unknown["recovery"]


def test_ambiguous_name_does_not_choose_a_piece(knowledge, housing, db):
    piece, _, _ = housing
    other = create_random_part(db, name="Pump Housing")
    try:
        seed = knowledge.initial_lookup(ORIGINAL_QUESTION)
        result = knowledge.run(*seed)
        assert result["error_code"] == "ambiguous_entity"
        assert not result["retryable"]
        assert other.code in result["error"]
        assert piece.code in result["error"]
        seed = knowledge.initial_lookup(
            f"Qué corrección tiene N170 del Bolt Eye de Pump Housing, pieza {piece.code}?"
        )
        assert knowledge.run(*seed)["part"] == piece.code
    finally:
        db.delete(other)
        db.commit()


def test_current_question_scope_rejects_other_feature_and_cota(knowledge, housing):
    piece, _, ribs = housing
    knowledge.initial_lookup(ORIGINAL_QUESTION)
    for tool, args in [
        ("read_feature", {"feature_id": str(ribs.id)}),
        ("read_part", {"part": piece.code, "characteristic": "N999"}),
    ]:
        result = knowledge.run(tool, args)
        assert result["error_code"] == "scope_mismatch"
        assert result["required_scope"]["characteristic"] == "N170"
    catalog = knowledge.run("search_catalog", {"query": "Pump Housing"})
    assert [f["name"] for f in catalog["features"]] == ["Bolt Eye"]
    assert [c["code"] for c in catalog["characteristics"]] == ["N170"]


def test_no_invented_link_between_feature_and_cota(knowledge, housing):
    piece, _, ribs = housing
    result = knowledge.run(
        "read_part",
        {
            "part": piece.code,
            "feature_id": str(ribs.id),
            "section": "corrections",
            "characteristic": "N170",
        },
    )
    assert result["error_code"] == "unverified_relationship"
    assert not result["retryable"]


def test_feature_corrections_without_cota_exclude_other_features(
    knowledge, housing, db
):
    piece, bolt, _ = housing
    job = db.get(EvidenceJob, job_id("study", piece.id))
    job.payload = {
        **job.payload,
        "action_index": {
            **job.payload["action_index"],
            "1.9": {
                "id": "1.9",
                "features": ["N999"],
                "paragraphs": ["Retoque ajeno al Bolt Eye"],
            },
        },
    }
    db.add(job)
    db.commit()
    result = knowledge.run(
        "read_part",
        {"part": piece.code, "feature_id": str(bolt.id), "section": "corrections"},
    )
    assert [action["id"] for action in result["actions"]] == ["1.2"]


def test_followup_preserves_explicit_cota_without_guessing_part(knowledge):
    assert knowledge.initial_lookup("Y las correcciones de N170?") is None
    assert knowledge.scope == {"characteristic": "N170"}


def test_catalog_typo_and_exact_name_win_over_newer_related_feature(
    knowledge, housing, db
):
    from app import crud

    _, bolt, ribs = housing
    ribs.description = "Notas relacionadas con Bolt Eye"
    db.add(ribs)
    db.commit()
    result = knowledge.run("search_catalog", {"query": "bold eye"})
    assert [f["name"] for f in result["features"]] == ["Bolt Eye"]
    found, _ = crud.search_features(session=db, q="Bolt Eye", limit=1)
    assert found[0].id == bolt.id


def test_original_question_uses_corrections_and_discards_wrong_previous_answer(
    client, normal_user_token_headers, monkeypatch, housing
):
    piece, _, _ = housing

    class Provider:
        async def stream(self, messages, tools):
            raise AssertionError(
                "A complete factual correction is rendered from its source"
            )
            yield

    monkeypatch.setattr(assistant_router, "get_provider", lambda _: Provider())
    response = client.post(
        f"{API}/chat",
        headers=normal_user_token_headers,
        json={
            "messages": [
                {"role": "user", "content": "Qué pasa con los Nervios?"},
                {"role": "assistant", "content": "Pump Housing no tiene Nervios."},
                {"role": "user", "content": ORIGINAL_QUESTION},
            ]
        },
    )
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[-1]["type"] == "done"
    reply = "".join(e.get("text", "") for e in events if e["type"] == "delta")
    assert "N170" in reply and piece.code in reply and "Bolt Eye" in reply
    assert "Nervios" not in reply and "> Propuesta de ajuste" in reply
    assert "3,9–4 mm" in reply and "no acredita la ejecución" in reply


def test_three_dependent_reads_can_finish_before_drafting(
    client, normal_user_token_headers, monkeypatch, housing
):
    piece, bolt, _ = housing
    calls = []

    class Provider:
        async def stream(self, messages, tools):
            calls.append(messages)
            steps = [
                ("search_catalog", {"query": piece.code}),
                ("read_feature", {"feature_id": str(bolt.id)}),
                (
                    "read_part",
                    {
                        "part": piece.code,
                        "section": "corrections",
                        "characteristic": "N170",
                    },
                ),
            ]
            if len(calls) <= 3:
                assert tools
                name, args = steps[len(calls) - 1]
                yield ModelChunk(
                    content="Voy a consultar.",
                    tool_calls=[{"function": {"name": name, "arguments": args}}],
                )
            else:
                assert not tools
                assert "Propuesta de ajuste" in messages[-1]["content"]
                assert "Nervios" not in messages[-1]["content"]
                yield ModelChunk(content="La corrección propone un ajuste.")

    monkeypatch.setattr(assistant_router, "get_provider", lambda _: Provider())
    response = client.post(
        f"{API}/chat",
        headers=normal_user_token_headers,
        json={
            "messages": [
                {"role": "user", "content": "Localiza un caso y explica su corrección"}
            ]
        },
    )
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[-1]["type"] == "done" and len(calls) == 4
    answer = "".join(e.get("text", "") for e in events if e["type"] == "delta")
    assert answer == "La corrección propone un ajuste."


def test_failed_lookup_cannot_be_published_as_absence_of_corrections(
    client, normal_user_token_headers, monkeypatch
):
    rounds = []

    class Provider:
        async def stream(self, messages, tools):
            rounds.append(messages)
            if len(rounds) == 1:
                yield ModelChunk(
                    tool_calls=[
                        {
                            "function": {
                                "name": "read_part",
                                "arguments": {
                                    "part": "unknown-piece",
                                    "section": "corrections",
                                },
                            }
                        }
                    ]
                )
            else:
                yield ModelChunk(content="La pieza no existe y no tiene correcciones.")

    monkeypatch.setattr(assistant_router, "get_provider", lambda _: Provider())
    response = client.post(
        f"{API}/chat",
        headers=normal_user_token_headers,
        json={
            "messages": [
                {"role": "user", "content": "Qué correcciones hay para unknown-piece?"}
            ]
        },
    )
    events = [json.loads(line) for line in response.text.splitlines()]
    answer = "".join(e.get("text", "") for e in events if e["type"] == "delta")
    assert "La pieza no existe" not in answer
    assert "No he podido verificar" in answer
    assert events[-1]["type"] == "done"
