"""The Codex adapter must keep the existing authenticated chat and source contract."""

import json

import httpx

from app.assistant.config import AssistantSettings, get_settings
from app.main import app
from tests.utils.feature import create_random_feature, create_random_note


def test_codex_uses_imported_notes_and_existing_chat_events(
    client, db, normal_user_token_headers, monkeypatch
):
    feature = create_random_feature(db, name="Feature ficticio prueba Codex")
    note = create_random_note(db, feature)
    note.title = "Evitar aristas vivas"
    note.body = "Nota sintética para la prueba del adaptador."
    db.add(note)
    db.commit()
    app.dependency_overrides[get_settings] = lambda: AssistantSettings(
        _env_file=None, enabled=True, provider="codex", model="test-model",
        codex_bridge_token="private-synthetic-bridge-token-1234567890",
    )
    original = httpx.AsyncClient
    calls = []

    def handler(request):
        payload = json.loads(request.content)
        calls.append(payload)
        assert "Evitar aristas vivas" in json.dumps(payload, ensure_ascii=False)
        return httpx.Response(200, text=(
            '{"type":"chunk","content":"La advertencia es evitar aristas vivas.","tool_calls":[]}\n'
            '{"type":"done"}\n'
        ))

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original(
        **kwargs, transport=httpx.MockTransport(handler),
    ))
    try:
        response = client.post(
            "/api/v1/assistant/chat", headers=normal_user_token_headers,
            json={"messages": [{"role": "user", "content": f"¿Qué advertencias tiene {feature.name}?"}]},
        )
        events = [json.loads(line) for line in response.text.splitlines() if line]
        assert response.status_code == 200
        assert len(calls) == 1
        assert {event["type"] for event in events} == {"status", "delta", "sources", "done"}
        assert next(event for event in events if event["type"] == "sources")["sources"]
        assert next(event for event in events if event["type"] == "delta")["text"] == "La advertencia es evitar aristas vivas."
    finally:
        app.dependency_overrides.pop(get_settings, None)
