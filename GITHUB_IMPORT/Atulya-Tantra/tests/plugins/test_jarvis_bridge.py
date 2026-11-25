"""Atulya can read JARVIS on loopback only; the model cannot choose a URL."""
from __future__ import annotations

import asyncio
import json

import httpx

from tools.plugins import toolkit
from tools.plugins.toolkit import TOOLS, VOICE_TOOLS


def test_jarvis_status_is_a_direct_voice_capability() -> None:
    names = {tool.name for tool in TOOLS}
    assert "jarvis_status" in names
    assert "jarvis_status" in VOICE_TOOLS
    tool = next(tool for tool in TOOLS if tool.name == "jarvis_status")
    assert tool.confirm is False
    assert tool.admin_only is False
    schema = tool.schema()["function"]["parameters"]
    assert set(schema["properties"]) == {"view"}
    assert schema["additionalProperties"] is False


def test_jarvis_status_only_calls_fixed_loopback_paths(monkeypatch) -> None:
    calls: list[str] = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, url: str):
            calls.append(url)
            return httpx.Response(200, json={"ok": True, "path": url})

    monkeypatch.setattr(toolkit.httpx, "AsyncClient", FakeClient)
    tool = next(item for item in TOOLS if item.name == "jarvis_status")
    reply = asyncio.run(tool.handler({"view": "capabilities"}, None))
    assert calls == ["http://127.0.0.1:3860/jarvis/api/jarvis/capabilities"]
    assert json.loads(reply)["path"] == calls[0]


def test_jarvis_status_rejects_model_supplied_url(monkeypatch) -> None:
    tool = next(item for item in TOOLS if item.name == "jarvis_status")
    try:
        asyncio.run(tool.handler({"view": "capabilities", "url": "https://example.com"}, None))
    except ValueError as exc:
        assert "view" in str(exc)
    else:
        raise AssertionError("model-supplied URL must be rejected")
