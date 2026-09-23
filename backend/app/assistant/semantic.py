"""Hybrid text retrieval over current app data and a replaceable vector cache."""

import json
import math
import re
import unicodedata
from collections import Counter
from typing import TYPE_CHECKING, Any

from sqlalchemy import text
from sqlmodel import Session, select

from app.assistant.config import AssistantSettings
from app.assistant.corpus import Passage, collect, in_scope
from app.assistant.embeddings import (
    EmbeddingError,
    OllamaEmbeddings,
    model_key,
    query_input,
)
from app.assistant.index_models import AssistantEmbedding

if TYPE_CHECKING:
    from app.assistant.tools import KnowledgeSearch

STOP = set(
    "a al algo ante bajo con como cual de del desde donde el en entre es esta este estos esa eso hay la las lo los me mi para por que qué se sin sobre su sus un una unos unas y o the of to in and for is are what how les els amb per dels las quiero saber dime pregunta información informacion tiene tienen tenemos hemos".split()
)


def tokens(value: str) -> list[str]:
    normalized = "".join(
        c
        for c in unicodedata.normalize("NFD", value.casefold())
        if not unicodedata.combining(c)
    )
    return [t for t in re.findall(r"\w+", normalized) if t not in STOP]


def lexical_rank(query: str, docs: list[Passage]) -> list[str]:
    """BM25 on the small live corpus; identifiers retain exact token matches."""
    terms = set(tokens(query))
    bags = [Counter(tokens(d.title + " " + d.text)) for d in docs]
    avg_length = sum(sum(b.values()) for b in bags) / max(len(bags), 1) or 1
    frequencies = Counter(t for b in bags for t in terms if b[t])
    scores = []
    for doc, bag in zip(docs, bags, strict=True):
        score = 0.0
        for term in terms:
            freq = bag[term]
            if freq:
                inverse = math.log(
                    1
                    + (len(docs) - frequencies[term] + 0.5) / (frequencies[term] + 0.5)
                )
                score += (
                    inverse
                    * freq
                    * 2.2
                    / (freq + 1.2 * (0.25 + 0.75 * sum(bag.values()) / avg_length))
                )
        if score:
            scores.append((score, doc.id))
    return [key for _, key in sorted(scores, key=lambda x: (-x[0], x[1]))[:30]]


def search(
    session: Session, args: "KnowledgeSearch", settings: AssistantSettings
) -> dict[str, Any]:
    characteristic = (args.characteristic or "").upper().replace(" ", "") or None
    if characteristic and characteristic[0].isdigit():
        characteristic = "N" + characteristic
    docs = [
        d
        for d in collect(session)
        if in_scope(
            d,
            part=args.part,
            feature_id=str(args.feature_id) if args.feature_id else None,
            revision=args.revision,
            characteristic=characteristic,
        )
    ]
    lexical = lexical_rank(args.query, docs)
    semantic: list[str] = []
    state = "disabled"
    indexed = 0
    if settings.semantic_enabled and docs:
        cached = dict(
            session.exec(
                select(AssistantEmbedding.id, AssistantEmbedding.fingerprint).where(
                    AssistantEmbedding.model == model_key(settings)
                )
            ).all()
        )
        current = [d for d in docs if cached.get(d.id) == d.fingerprint]
        indexed = len(current)
        state = "ready" if indexed == len(docs) else "indexing"
        if current:
            try:
                vector = OllamaEmbeddings(settings).embed([query_input(args.query)])[0]
                # Exact cosine retrieval is appropriate for this small corpus. Live
                # fingerprint joins exclude edits/deletions before reindexing finishes.
                rows = session.execute(
                    text("""
                    SELECT e.id, 1 - (e.embedding <=> CAST(:vector AS vector)) AS similarity
                    FROM assistant_embedding e
                    JOIN jsonb_to_recordset(CAST(:documents AS jsonb))
                      AS live(id text, fingerprint text)
                      ON e.id = live.id AND e.fingerprint = live.fingerprint
                    WHERE e.model = :model
                    ORDER BY e.embedding <=> CAST(:vector AS vector), e.id
                    LIMIT 30
                """),
                    {
                        "vector": json.dumps(vector),
                        "model": model_key(settings),
                        "documents": json.dumps(
                            [
                                {"id": d.id, "fingerprint": d.fingerprint}
                                for d in current
                            ]
                        ),
                    },
                ).all()
                semantic = [
                    row.id
                    for row in rows
                    if row.similarity >= settings.semantic_min_similarity
                ]
            except EmbeddingError:
                state = "unavailable"
    elif settings.semantic_enabled:
        state = "ready"
    # Reciprocal rank fusion; neither scores nor vector distance mean confidence.
    scores: dict[str, float] = {}
    for ranking in (lexical, semantic):
        for position, key in enumerate(ranking, 1):
            scores[key] = scores.get(key, 0.0) + 1 / (60 + position)
    by_id = {d.id: d for d in docs}
    hits = []
    seen: set[str] = set()
    for key in sorted(scores, key=lambda k: (-scores[k], k)):
        doc = by_id[key]
        if doc.source_id in seen:
            continue
        seen.add(doc.source_id)
        hits.append(
            {"title": doc.title, "text": doc.text, "url": doc.url, "scope": doc.scope}
        )
        if len(hits) == 6:
            break
    return {
        "hits": hits,
        "mode": "hybrid" if semantic else "lexical",
        "semantic_status": state,
        "indexed_passages": indexed,
        "eligible_passages": len(docs),
        "notice": "Selección por relevancia, no inventario completo. Lee la ficha para enumerar sus notas. Los retoques son propuestas, no ejecución confirmada.",
        **(
            {
                "retrieval_warning": "Solo se ha podido buscar por palabras; la búsqueda semántica está temporalmente indisponible."
            }
            if state == "unavailable"
            else {}
        ),
    }
