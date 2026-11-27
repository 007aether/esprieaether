"""Le modèle local 3B reçoit des schémas d'outils minimaux : la réponse arrive avant la deadline."""
from __future__ import annotations

import asyncio
import json

import httpx

from tools.plugins.brain import Message, OpenAICompatibleProvider

TOOLS = [{
    "type": "function",
    "function": {
        "name": "do_thing",
        "description": "A deliberately verbose description " * 12,
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "A verbose parameter description " * 8},
            },
            "required": ["city"],
        },
    },
}]


def _sent_tools(base_url: str) -> list[dict]:
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, text="data: [DONE]\n\n",
                              headers={"content-type": "text/event-stream"})

    provider = OpenAICompatibleProvider(
        base_url=base_url, model="m",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    async def run() -> None:
        [_ async for _ in provider.stream([Message(role="user", content="hi")], tools=TOOLS)]

    asyncio.run(run())
    return seen[0]["tools"]


def test_loopback_tools_are_minimal_but_keep_names_and_arguments() -> None:
    sent = _sent_tools("http://127.0.0.1:31416/v1")
    fn = sent[0]["function"]
    assert fn["name"] == "do_thing"
    assert "description" not in fn
    assert fn["parameters"]["required"] == ["city"]
    assert fn["parameters"]["properties"]["city"] == {"type": "string"}
    assert TOOLS[0]["function"]["description"] == "A deliberately verbose description " * 12


def test_external_provider_keeps_full_schemas() -> None:
    assert _sent_tools("https://example.invalid/v1") == TOOLS
