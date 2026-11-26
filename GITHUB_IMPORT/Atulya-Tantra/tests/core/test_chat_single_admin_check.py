"""J140 — /api/chat vérifie le rôle admin une seule fois par requête."""
from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest
from conftest import authenticate_test_admin

import atulya.server as server
from atulya.settings import Settings
from tools.plugins.brain import Brain, Message


class StubProvider:
    name = "Local stub"
    model = "stub"

    async def complete(self, messages: list[Message]) -> str:
        return "local answer"

    async def stream(self, messages: list[Message]):
        yield "local answer"


def test_chat_ne_verifie_le_role_admin_qu_une_fois(
    project_temp_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = Settings(
        assistant_name="Atulya", host="127.0.0.1", port=8501,
        data_dir=project_temp_dir / "data", models_dir=project_temp_dir / "models",
        model_provider="", model_name="", model_base_url="", model_api_key="",
    )
    monkeypatch.setattr(server, "_make_brain", lambda _: Brain(StubProvider(), assistant_name="Atulya"))
    app = server.create_app(settings)
    store = app.state.auth_store
    original = store.is_admin
    calls: list[str] = []

    def counted(user_id: str) -> bool:
        calls.append(user_id)
        return original(user_id)

    store.is_admin = counted  # type: ignore[method-assign]

    async def exercise() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
            authenticate_test_admin(client, app)
            return await client.post(
                "/api/chat", json={"messages": [{"role": "user", "content": "Hello Atulya"}]}
            )

    response = asyncio.run(exercise())
    assert response.status_code == 200
    assert len(calls) == 1
