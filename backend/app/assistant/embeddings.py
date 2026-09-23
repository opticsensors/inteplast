"""Local embedding provider; independent of the conversational model."""

import math
from typing import Protocol

import httpx

from app.assistant.config import AssistantSettings


class EmbeddingError(Exception):
    pass


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OllamaEmbeddings:
    def __init__(self, settings: AssistantSettings) -> None:
        self.settings = settings

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            with httpx.Client(
                base_url=self.settings.ollama_url.rstrip("/"),
                timeout=httpx.Timeout(
                    self.settings.embedding_timeout_seconds, connect=3
                ),
                trust_env=False,
            ) as client:
                response = client.post(
                    "/api/embed",
                    json={
                        "model": self.settings.embedding_model,
                        "input": texts,
                        "dimensions": self.settings.embedding_dimensions,
                        "truncate": False,
                        "keep_alive": "15m",
                    },
                )
                response.raise_for_status()
                vectors = response.json()["embeddings"]
            if not isinstance(vectors, list) or len(vectors) != len(texts):
                raise ValueError("Invalid embedding batch")
            for vector in vectors:
                if (
                    len(vector) != self.settings.embedding_dimensions
                    or not all(
                        isinstance(v, (int, float))
                        and not isinstance(v, bool)
                        and math.isfinite(v)
                        for v in vector
                    )
                    or not any(vector)
                ):
                    raise ValueError("Invalid embedding vector")
            return vectors
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            raise EmbeddingError(
                "El buscador semántico local no está disponible."
            ) from error


def model_key(settings: AssistantSettings) -> str:
    # Bump the recipe version when chunking/prompt conventions change.
    return f"{settings.embedding_model}:{settings.embedding_dimensions}:v1"


def document_input(title: str, body: str) -> str:
    return f"title: {title} | text: {body}"


def query_input(query: str) -> str:
    return f"task: search result | query: {query}"
