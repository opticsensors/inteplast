from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AssistantSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ASSISTANT_",
        env_file=Path(__file__).resolve().parents[3] / ".env",
        extra="ignore",
    )

    enabled: bool = False
    provider: Literal["ollama", "codex"] = "ollama"
    ollama_url: str = "http://127.0.0.1:11434"
    codex_bridge_url: str = "http://host.docker.internal:11435"
    codex_bridge_token: SecretStr = SecretStr("")
    model: str = "qwen3.5:2b"
    context_tokens: int = Field(default=8192, ge=4096, le=32768)
    max_tokens: int = Field(default=1024, ge=64, le=4096)
    timeout_seconds: int = Field(default=120, ge=10, le=300)
    semantic_enabled: bool = True
    embedding_model: str = "embeddinggemma"
    embedding_dimensions: int = Field(default=768, ge=128, le=4096)
    semantic_min_similarity: float = Field(default=0.24, ge=0, le=1)
    embedding_timeout_seconds: int = Field(default=30, ge=5, le=120)
    index_interval_seconds: int = Field(default=60, ge=10, le=3600)

    @model_validator(mode="after")
    def validate_codex(self) -> "AssistantSettings":
        if self.provider == "codex":
            if self.enabled and len(self.codex_bridge_token.get_secret_value()) < 32:
                raise ValueError(
                    "Codex requires a private bridge token of at least 32 characters"
                )
            # The local proof of concept must never fall back to Ollama embeddings.
            self.semantic_enabled = False
        return self


@lru_cache
def get_settings() -> AssistantSettings:
    return AssistantSettings()
