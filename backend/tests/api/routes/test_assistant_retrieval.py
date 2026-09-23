import copy
import json
import math

import httpx
import pytest
from sqlmodel import select

from app.assistant import semantic
from app.assistant.config import AssistantSettings
from app.assistant.corpus import collect
from app.assistant.drafting import messages as drafting_messages
from app.assistant.embeddings import EmbeddingError, OllamaEmbeddings
from app.assistant.index import sync_batch
from app.assistant.index_models import AssistantEmbedding
from app.assistant.service import bounded_result
from app.assistant.summaries import measurements, page
from app.assistant.tools import KnowledgeSearch, KnowledgeTools
from app.core.config import settings
from app.knowledge_models import FeatureCharacteristicLink, PartCharacteristic
from app.models import FeatureNote, User
from tests.utils.feature import create_random_feature, create_random_part


def test_assistant_summary_covers_later_cavities_and_separates_limits_and_units():
    records = {
        f"c{c}": {
            f"{s:02}": {
                "value": c + s / 10,
                "lower": 10,
                "upper": 20,
                "nominal": 15,
                "status": "inside",
                "source": {"path": f"private/c{c}.csv"},
            }
            for s in range(1, 5)
        }
        for c in range(13, 17)
    }
    series = {"id": "gx-1", "label": "B1 H1.5 GX", "unit": "mm", "records": records}
    other = copy.deepcopy(series)
    other.update(id="angle", label="Ángulo", unit="deg")
    # Same series with changed limits must be a separate aggregate.
    records["c16"]["04"].update(value=21, upper=19, status="outside")
    summary, groups, rows = measurements(
        [{"id": "N170", "series": [series, other]}], cavity=None, sample=None
    )
    assert summary["cavities"] == ["c13", "c14", "c15", "c16"]
    assert summary["total"] == 32 and summary["samples"] == ["01", "02", "03", "04"]
    assert summary["status_counts"] == {"inside": 31, "outside": 1}
    assert len(groups) == 3
    assert summary["series_total"] == 2 and summary["statistical_groups_total"] == 3
    assert groups[0]["count"] == 15 and groups[0]["min"] == 13.1
    assert groups[1]["count"] == 1 and groups[1]["max"] == 21
    result = {
        "summary": summary,
        "series_summaries": groups,
        "rows": rows[:8],
        "coverage": {"rows": page(32, 0, 8), "series_summaries": page(3, 0, 3)},
    }
    compact = json.loads(bounded_result(result, 2200))
    assert compact["summary"] == summary
    assert compact["coverage"]["rows"]["complete"] is False
    assert compact["coverage"]["rows"]["returned"] == len(compact["rows"])
    assert compact["coverage"]["rows"]["next_offset"] == len(compact["rows"])
    filtered, _, _ = measurements(
        [{"id": "N170", "series": [series]}], cavity="c16", sample="04"
    )
    assert filtered["total"] == 1 and filtered["status_counts"] == {"outside": 1}


def test_assistant_feature_reads_all_ten_notes_and_reports_budget_trimming(
    db, normal_user_token_headers
):
    assert normal_user_token_headers
    user = db.exec(select(User).where(User.email == settings.EMAIL_TEST_USER)).one()
    feature = create_random_feature(db)
    for n in range(10):
        db.add(
            FeatureNote(
                feature_id=feature.id,
                kind="warning",
                title=f"Nota {n}",
                body="Texto " * 20,
                position=n,
            )
        )
    db.commit()
    knowledge = KnowledgeTools(user.id, AssistantSettings(semantic_enabled=False))
    result = knowledge.run("read_feature", {"feature_id": str(feature.id)})
    assert len(result["notes"]) == 10 and result["coverage"]["notes"]["complete"]
    assert knowledge.initial_lookup(f"Advertencias de {feature.name}") == (
        "read_feature",
        {"feature_id": str(feature.id)},
    )
    compact = json.loads(bounded_result(result, 1500))
    coverage = compact["coverage"]["notes"]
    assert coverage["total"] == 10 and not coverage["complete"]
    assert coverage["next_offset"] == len(compact["notes"])
    rest = knowledge.run(
        "read_feature",
        {"feature_id": str(feature.id), "offset": coverage["next_offset"]},
    )
    assert len(rest["notes"]) + len(compact["notes"]) == 10


class Embedder:
    def __init__(self):
        self.calls = 0

    def embed(self, texts):
        self.calls += 1
        vectors = []
        for value in texts:
            if "encogimiento" in value.lower():
                # Relevant paraphrases need not have near-identical vectors.
                vector = [0.26, math.sqrt(1 - 0.26**2), 0.0]
            elif "contracción" in value.lower():
                vector = [1.0, 0.0, 0.0]
            else:
                vector = [0.0, 0.0, 1.0]
            vectors.append(vector + [0.0] * 125)
        return vectors


@pytest.fixture
def indexed_note(db, monkeypatch):
    feature = create_random_feature(db)
    part = create_random_part(db)
    cota = PartCharacteristic(part_id=part.id, code="N170", revision="06")
    note = FeatureNote(
        feature_id=feature.id,
        kind="warning",
        title="Contracción diferencial",
        body="Las diferencias de espesor desplazan los agujeros.",
    )
    db.add(cota)
    db.add(note)
    db.commit()
    db.add(
        FeatureCharacteristicLink(
            feature_id=feature.id, characteristic_id=cota.id, role="primary"
        )
    )
    db.commit()
    configuration = AssistantSettings(semantic_enabled=True, embedding_dimensions=128)
    embedder = Embedder()
    while sync_batch(configuration, embedder):
        pass
    monkeypatch.setattr(semantic, "OllamaEmbeddings", lambda _: embedder)
    return feature, part, note, configuration, embedder


def test_assistant_hybrid_finds_synonyms_and_filters_piece_revision_cota(
    db, indexed_note
):
    feature, part, note, configuration, embedder = indexed_note
    query = "encogimiento al enfriarse"
    docs = collect(db)
    passage = next(d for d in docs if d.source_id == f"note:{note.id}")
    assert passage.id not in semantic.lexical_rank(query, docs)
    result = semantic.search(
        db,
        KnowledgeSearch(
            query=query, part=part.code, revision="06", characteristic="N170"
        ),
        configuration,
    )
    assert result["mode"] == "hybrid" and result["semantic_status"] == "ready"
    assert result["hits"][0]["title"].endswith("Contracción diferencial")
    assert result["hits"][0]["url"] == f"/features/{feature.id}"
    for filters in (
        {"part": "missing"},
        {"revision": "07"},
        {"characteristic": "N999"},
    ):
        result = semantic.search(
            db,
            KnowledgeSearch(query=query, feature_id=feature.id, **filters),
            configuration,
        )
        assert not result["hits"]
    calls = embedder.calls
    assert sync_batch(configuration, embedder) == 0
    assert embedder.calls == calls  # Unchanged content is never re-embedded.


def test_assistant_stale_embeddings_never_serve_edited_or_deleted_content(
    db, indexed_note
):
    feature, _, note, configuration, embedder = indexed_note
    key = f"note:{note.id}:0"
    note.title, note.body = "Nueva nota", "Comprobar acabado visual."
    db.add(note)
    db.commit()
    result = semantic.search(
        db, KnowledgeSearch(query="encogimiento", feature_id=feature.id), configuration
    )
    assert not result["hits"] and result["semantic_status"] == "indexing"
    while sync_batch(configuration, embedder):
        pass
    assert db.get(AssistantEmbedding, key) is not None
    db.delete(note)
    db.commit()
    result = semantic.search(
        db, KnowledgeSearch(query="Nueva nota", feature_id=feature.id), configuration
    )
    assert not any(h["title"].endswith("Nueva nota") for h in result["hits"])
    sync_batch(configuration, embedder)
    db.expire_all()
    assert db.get(AssistantEmbedding, key) is None


def test_assistant_semantic_outage_preserves_lexical_search(
    db, indexed_note, monkeypatch
):
    feature, _, _, configuration, _ = indexed_note

    class Offline:
        def embed(self, _texts):
            raise EmbeddingError("offline")

    monkeypatch.setattr(semantic, "OllamaEmbeddings", lambda _: Offline())
    result = semantic.search(
        db, KnowledgeSearch(query="Contracción", feature_id=feature.id), configuration
    )
    assert result["mode"] == "lexical" and result["semantic_status"] == "unavailable"
    assert result["hits"] and result["retrieval_warning"]


def test_assistant_embedding_contract_validates_dimensions_and_disables_truncation(
    monkeypatch,
):
    valid = True

    def handle(request):
        payload = json.loads(request.content)
        assert payload["model"] == "embeddinggemma" and payload["truncate"] is False
        assert payload["dimensions"] == 128
        return httpx.Response(
            200, json={"embeddings": [[1.0] + [0.0] * (127 if valid else 5)]}
        )

    original = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kw: original(**kw, transport=httpx.MockTransport(handle)),
    )
    provider = OllamaEmbeddings(AssistantSettings(embedding_dimensions=128))
    assert len(provider.embed(["texto"])[0]) == 128
    valid = False
    with pytest.raises(EmbeddingError):
        provider.embed(["texto"])


def test_assistant_drafting_uses_passages_without_tool_names_or_private_ids():
    result = {
        "hits": [
            {
                "title": "Nota de contracción",
                "text": "La contracción desplaza el agujero.",
                "scope": {
                    "feature_id": "private-id",
                    "feature": "Bolt Eye",
                    "parts": ["3212"],
                },
            }
        ],
        "notice": "Call read_feature using feature_id",
        "semantic_status": "ready",
    }
    prompt = drafting_messages(
        [{"role": "user", "content": "Problemas al enfriarse"}], [result]
    )
    content = prompt[-1]["content"]
    assert "La contracción desplaza el agujero" in content and "3212" in content
    assert (
        "read_feature" not in content
        and "feature_id" not in content
        and "private-id" not in content
    )
