"""Incremental background indexing. Only this worker writes the derived cache."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, col, delete, select

from app.assistant.config import AssistantSettings, get_settings
from app.assistant.corpus import collect
from app.assistant.embeddings import (
    EmbeddingProvider,
    OllamaEmbeddings,
    document_input,
    model_key,
)
from app.assistant.index_models import AssistantEmbedding
from app.core.db import engine

logger = logging.getLogger(__name__)


def sync_batch(
    settings: AssistantSettings, provider: EmbeddingProvider | None = None
) -> int:
    """Return remaining passages. A DB lock prevents duplicate work across processes."""
    with Session(engine) as session:
        if not session.execute(
            text("SELECT pg_try_advisory_xact_lock(482913721)")
        ).scalar():
            return 0
        docs = collect(session)
        current = {d.id: d.fingerprint for d in docs}
        rows = session.exec(
            select(
                AssistantEmbedding.id,
                AssistantEmbedding.fingerprint,
                AssistantEmbedding.model,
            )
        ).all()
        cached = {
            key: fingerprint
            for key, fingerprint, model in rows
            if model == model_key(settings)
        }
        stale = [key for key, _, _ in rows if key not in current]
        if stale:
            session.exec(
                delete(AssistantEmbedding).where(col(AssistantEmbedding.id).in_(stale))
            )
        pending = [d for d in docs if cached.get(d.id) != d.fingerprint]
        batch = pending[:4]
        if batch:
            embedder = provider or OllamaEmbeddings(settings)
            vectors = embedder.embed([document_input(d.title, d.text) for d in batch])
            for doc, vector in zip(batch, vectors, strict=True):
                statement = insert(AssistantEmbedding).values(
                    id=doc.id,
                    fingerprint=doc.fingerprint,
                    model=model_key(settings),
                    embedding=vector,
                )
                session.execute(
                    statement.on_conflict_do_update(
                        index_elements=["id"],
                        set_={
                            "fingerprint": statement.excluded.fingerprint,
                            "model": statement.excluded.model,
                            "embedding": statement.excluded.embedding,
                        },
                    )
                )
        session.commit()
    return max(0, len(pending) - len(batch))


@asynccontextmanager
async def index_lifespan(_app: Any) -> AsyncIterator[None]:
    settings = get_settings()
    stop = asyncio.Event()

    async def worker() -> None:
        while not stop.is_set():
            delay = settings.index_interval_seconds
            try:
                pending = await asyncio.to_thread(sync_batch, settings)
                if pending:
                    delay = 1
            except Exception:
                logger.warning(
                    "Assistant text index unavailable; lexical search remains available",
                    exc_info=True,
                )
            try:
                await asyncio.wait_for(stop.wait(), timeout=delay)
            except asyncio.TimeoutError:
                pass

    task = (
        asyncio.create_task(worker())
        if settings.enabled and settings.semantic_enabled
        else None
    )
    try:
        yield
    finally:
        stop.set()
        if task:
            await task


if __name__ == "__main__":
    configuration = get_settings()
    while sync_batch(configuration):
        pass
    logger.warning("Assistant text index is up to date")
