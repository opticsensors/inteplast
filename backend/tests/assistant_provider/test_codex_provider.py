"""Standalone adapter tests: no application database or working credentials."""

import asyncio
import json

import httpx
import pytest

from app.assistant.codex_provider import CodexProvider
from app.assistant.config import AssistantSettings
from app.assistant.providers import ProviderError, get_provider

TOKEN = "isolated-bridge-test-token-1234567890"
MESSAGES = [{"role": "user", "content": "Consulta de prueba"}]
TOOLS = [{"type": "function", "function": {"name": "read_part"}}]


def settings(**kwargs):
    return AssistantSettings(
        _env_file=None, provider="codex", model="test-model",
        codex_bridge_token=TOKEN, **kwargs,
    )


def transport(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(
        **kwargs, transport=httpx.MockTransport(handler),
    ))


def collect(config=None):
    async def run():
        return [chunk async for chunk in CodexProvider(config or settings()).stream(MESSAGES, TOOLS)]
    return asyncio.run(run())


def test_codex_factory_disables_ollama_embeddings_and_hides_private_token():
    config = settings(semantic_enabled=True)
    assert not config.semantic_enabled
    assert isinstance(get_provider(config), CodexProvider)
    assert TOKEN not in repr(config)
    with pytest.raises(ValueError):
        AssistantSettings(_env_file=None, enabled=True, provider="codex", codex_bridge_token="short")


def test_disabled_codex_does_not_require_credentials_or_start_ollama():
    config = AssistantSettings(_env_file=None, enabled=False, provider="codex")
    assert not config.enabled
    assert not config.semantic_enabled


def test_round_trip_uses_private_backend_auth_and_preserves_tool_calls(monkeypatch):
    def handler(request):
        assert request.headers["authorization"] == f"Bearer {TOKEN}"
        assert request.url.path == "/v1/chat"
        payload = json.loads(request.content)
        assert payload == {"model": "test-model", "messages": MESSAGES, "tools": TOOLS}
        chunk = {"type": "chunk", "content": "", "tool_calls": [
            {"function": {"name": "read_part", "arguments": {"part": "DEMO-1"}}},
        ]}
        return httpx.Response(200, text=json.dumps(chunk) + '\n{"type":"done"}\n')
    transport(monkeypatch, handler)
    chunks = collect()
    assert chunks[0].tool_calls[0]["function"]["arguments"] == {"part": "DEMO-1"}


@pytest.mark.parametrize("text", [
    '{"type":"chunk","content":"incomplete"}\n',
    '{"type":"done"}\n',
    '[]\n', 'not-json\n',
    '{"type":"chunk","content":"","tool_calls":[]}\n{"type":"done"}\n',
    '{"type":"chunk","content":"","tool_calls":[{"function":{"name":"delete_part","arguments":{}}}]}\n{"type":"done"}\n',
    '{"type":"chunk","content":"","tool_calls":[{"function":{"name":"read_part","arguments":[]}}]}\n{"type":"done"}\n',
])
def test_invalid_or_incomplete_response_never_reaches_the_service(monkeypatch, text):
    transport(monkeypatch, lambda _: httpx.Response(200, text=text))
    with pytest.raises(ProviderError):
        collect()


@pytest.mark.parametrize("status", [401, 409, 500, 504])
def test_http_errors_are_safe_and_clear(monkeypatch, status):
    transport(monkeypatch, lambda _: httpx.Response(status, text="PRIVATE TOKEN OR PROMPT"))
    with pytest.raises(ProviderError) as failure:
        collect()
    assert "PRIVATE" not in str(failure.value)


def test_connection_failure(monkeypatch):
    def unavailable(request):
        raise httpx.ConnectError("offline", request=request)
    transport(monkeypatch, unavailable)
    with pytest.raises(ProviderError, match="puente local"):
        collect()


def test_normal_response_has_the_existing_model_chunk_contract(monkeypatch):
    transport(monkeypatch, lambda _: httpx.Response(200, text=(
        '{"type":"chunk","content":"Respuesta con su fuente.","tool_calls":[],"truncated":false}\n'
        '{"type":"done"}\n'
    )))
    chunks = collect()
    assert len(chunks) == 1
    assert chunks[0].content == "Respuesta con su fuente."
    assert not chunks[0].tool_calls
    assert chunks[0].truncated is False
