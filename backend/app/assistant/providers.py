"""Provider contract. No database, HTTP routes or UI concerns in model adapters."""

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from app.assistant.config import AssistantSettings


class ProviderError(Exception):
    pass


@dataclass
class ModelChunk:
    content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    truncated: bool = False


class ChatProvider(Protocol):
    def stream(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> AsyncIterator[ModelChunk]: ...


class OllamaProvider:
    def __init__(self, settings: AssistantSettings) -> None:
        self.settings = settings

    async def stream(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> AsyncIterator[ModelChunk]:
        payload: dict[str, Any] = {
            "model": self.settings.model,
            "messages": messages,
            "think": False,
            "stream": True,
            "keep_alive": "15m",
            "options": {
                "temperature": 0.2,
                "num_ctx": self.settings.context_tokens,
                "num_predict": self.settings.max_tokens,
            },
        }
        if tools:
            payload["tools"] = tools
        try:
            async with httpx.AsyncClient(
                base_url=self.settings.ollama_url.rstrip("/"),
                timeout=httpx.Timeout(self.settings.timeout_seconds, connect=5),
                trust_env=False,
            ) as client:
                async with client.stream("POST", "/api/chat", json=payload) as response:
                    if response.status_code == 404:
                        raise ProviderError(
                            f"No se encuentra el modelo {self.settings.model} en Ollama."
                        )
                    response.raise_for_status()
                    done = False
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        data = json.loads(line)
                        if data.get("error"):
                            raise ProviderError(
                                "Ollama no ha podido completar la respuesta."
                            )
                        message = data.get("message", {})
                        # Deliberately never expose or retain message.thinking.
                        yield ModelChunk(
                            content=message.get("content", ""),
                            tool_calls=message.get("tool_calls", []),
                            truncated=data.get("done_reason") == "length",
                        )
                        if data.get("done"):
                            done = True
                            break
                    if not done:
                        raise ProviderError(
                            "Se ha interrumpido la conexión con Ollama."
                        )
        except httpx.ConnectError as error:
            raise ProviderError(
                "No se puede conectar con Ollama. Comprueba que está abierto en el PC."
            ) from error
        except httpx.TimeoutException as error:
            raise ProviderError(
                "Ollama ha tardado demasiado. Prueba una consulta más breve."
            ) from error
        except (httpx.HTTPError, ValueError) as error:
            raise ProviderError(
                "La respuesta de Ollama no está disponible. Inténtalo de nuevo."
            ) from error


def get_provider(settings: AssistantSettings) -> ChatProvider:
    return OllamaProvider(settings)
