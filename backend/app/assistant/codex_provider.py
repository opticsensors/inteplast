"""Use the local Codex bridge without changing the application's chat protocol."""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.assistant.config import AssistantSettings
from app.assistant.providers import ModelChunk, ProviderError


class CodexProvider:
    def __init__(self, settings: AssistantSettings) -> None:
        self.settings = settings

    async def stream(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> AsyncIterator[ModelChunk]:
        allowed = {tool["function"]["name"] for tool in tools}
        payload = {"model": self.settings.model, "messages": messages, "tools": tools}
        try:
            async with httpx.AsyncClient(
                base_url=self.settings.codex_bridge_url.rstrip("/"),
                headers={
                    "Authorization": f"Bearer {self.settings.codex_bridge_token.get_secret_value()}"
                },
                timeout=httpx.Timeout(self.settings.timeout_seconds, connect=5),
                trust_env=False,
            ) as client:
                async with client.stream("POST", "/v1/chat", json=payload) as response:
                    if response.status_code == 409:
                        raise ProviderError(
                            "El asistente está atendiendo otra consulta. Inténtalo en unos segundos."
                        )
                    if response.status_code == 401:
                        raise ProviderError(
                            "La conexión local con Codex no está autorizada."
                        )
                    response.raise_for_status()
                    done = False
                    received = False
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if len(line) > 256 * 1024:
                            raise ProviderError(
                                "La respuesta de Codex supera el límite."
                            )
                        data = json.loads(line)
                        if not isinstance(data, dict):
                            raise ValueError("Invalid bridge event")
                        if data.get("type") == "done":
                            done = True
                            break
                        if data.get("type") != "chunk" or received:
                            raise ValueError("Unexpected bridge event")
                        content = data.get("content", "")
                        calls = data.get("tool_calls", [])
                        if (
                            not isinstance(content, str)
                            or not isinstance(calls, list)
                            or len(calls) > 5
                        ):
                            raise ValueError("Invalid model chunk")
                        for call in calls:
                            function = (
                                call.get("function") if isinstance(call, dict) else None
                            )
                            if (
                                not isinstance(function, dict)
                                or function.get("name") not in allowed
                                or not isinstance(function.get("arguments"), dict)
                            ):
                                raise ValueError("Invalid tool call")
                        if not content.strip() and not calls:
                            raise ValueError("Empty model chunk")
                        received = True
                        chunk = ModelChunk(
                            content=content,
                            tool_calls=calls,
                            truncated=data.get("truncated") is True,
                        )
                    if not done or not received:
                        raise ProviderError("Se ha interrumpido la conexión con Codex.")
                    # Never hand partial/uncommitted tool calls to the application.
                    yield chunk
        except httpx.ConnectError as error:
            raise ProviderError(
                "No se puede conectar con Codex. Comprueba que el puente local está abierto."
            ) from error
        except httpx.TimeoutException as error:
            raise ProviderError(
                "Codex ha tardado demasiado. Prueba una consulta más breve."
            ) from error
        except (httpx.HTTPError, ValueError, KeyError) as error:
            raise ProviderError(
                "La respuesta de Codex no está disponible. Comprueba el puente local y su sesión."
            ) from error
