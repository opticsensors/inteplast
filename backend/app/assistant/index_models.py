"""Disposable assistant cache; application records remain the source of truth."""

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import Column
from sqlmodel import Field, SQLModel


class AssistantEmbedding(SQLModel, table=True):
    __tablename__ = "assistant_embedding"

    id: str = Field(primary_key=True, max_length=512)
    fingerprint: str = Field(max_length=64)
    model: str = Field(max_length=255)
    # Variable dimensions allow switching embedding providers without a migration.
    embedding: list[float] = Field(sa_column=Column(Vector(), nullable=False))
