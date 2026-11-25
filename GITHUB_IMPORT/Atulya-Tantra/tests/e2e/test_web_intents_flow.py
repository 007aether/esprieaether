"""End-to-end proof for the four narrow chat intents, without a language model.

Run with the local interpreter:
    python -m unittest discover -s tests/e2e -p 'test_web_intents_flow.py' -v
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import httpx

import atulya.server as server
from atulya.settings import Settings
from tools.plugins.brain import Brain, Message

os.environ["ATULYA_PRELOAD"] = "0"
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class NoModelProvider:
    name = "No model expected"
    model = "stub"

    def __init__(self) -> None:
        self.calls = 0

    def _unexpected(self, _messages: list[Message]) -> None:
        self.calls += 1
        raise AssertionError("this deterministic phrase must not reach the model")

    async def complete(self, messages: list[Message]) -> str:
        self._unexpected(messages)
        return ""

    async def stream(self, messages: list[Message]):
        self._unexpected(messages)
        yield ""


class WebIntentFlowTest(unittest.TestCase):
    def test_chat_uses_real_tools_without_calling_the_model(self) -> None:
        with TemporaryDirectory(prefix="atulya-web-intents-", dir=Path.cwd()) as tmp:
            root = Path(tmp)
            models = root / "models"
            models.mkdir()
            settings = Settings(
                assistant_name="Atulya", host="127.0.0.1", port=8501,
                data_dir=root / "data", models_dir=models,
                model_provider="", model_name="", model_base_url="", model_api_key="",
            )
            provider = NoModelProvider()
            with patch.object(server, "_make_brain", lambda _settings: Brain(provider, assistant_name="Atulya")):
                app = server.create_app(settings)

            async def events(response: httpx.Response) -> list[dict]:
                return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]

            async def exercise() -> None:
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
                    token = app.state.auth_store.create_session("admin")
                    client.cookies.set("atulya_session", token)
                    conversation = "web_intents_e2e"
                    before = (await client.get("/api/profile")).json()["profile"].get("preferred_name", "")
                    try:
                        saved = await client.post("/api/chat", json={
                            "conversation_id": conversation,
                            "messages": [{"role": "user", "content": "From now on please call me Captain."}],
                        })
                        self.assertEqual(saved.status_code, 200, saved.text)
                        self.assertIn("preferred_name = Captain", saved.json()["text"])
                        self.assertEqual(saved.json()["route"], "web_intent")
                        self.assertEqual(
                            (await client.get("/api/profile")).json()["profile"]["preferred_name"], "Captain")
                        addressed = await client.post("/api/chat", json={
                            "conversation_id": conversation,
                            "messages": [{"role": "user", "content":
                                          "What name should you use to address me? "
                                          "Answer with only my saved preferred name."}],
                        })
                        self.assertEqual(addressed.json()["text"], "Captain")
                        self.assertEqual(addressed.json()["route"], "web_intent")

                        await client.post("/api/memory", json={
                            "conversation_id": conversation, "fact": "my selftest code word is mango",
                        })
                        recalled = await client.post("/api/chat", json={
                            "conversation_id": conversation,
                            "messages": [{"role": "user", "content":
                                          "What is my selftest code word? Check your saved memories."}],
                            "stream": True,
                        })
                        recall_events = await events(recalled)
                        self.assertIn("mango", "".join(event.get("text", "") for event in recall_events))
                        self.assertTrue(any(event.get("done") is True and
                                            event.get("route") == "web_intent"
                                            for event in recall_events))

                        button = await client.post("/api/chat", json={
                            "conversation_id": conversation,
                            "messages": [{"role": "user", "content":
                                          "Give me an open_website button for https://example.com."}],
                            "stream": True,
                        })
                        button_events = await events(button)
                        self.assertTrue(any(event.get("ui", {}).get("type") == "link" and
                                            event["ui"]["url"] == "https://example.com"
                                            for event in button_events), button_events)
                        self.assertFalse(any("confirm" in event for event in button_events))

                        approval = await client.post("/api/chat", json={
                            "conversation_id": conversation,
                            "messages": [{"role": "user", "content": "Open the Calculator app."}],
                            "stream": True,
                        })
                        approval_events = await events(approval)
                        confirms = [event["confirm"] for event in approval_events if "confirm" in event]
                        self.assertEqual(len(confirms), 1, approval_events)
                        self.assertIn("Calculator", confirms[0]["summary"])
                        denied = await client.post(f"/api/actions/{confirms[0]['id']}", json={"approve": False})
                        self.assertEqual(denied.status_code, 200)
                        self.assertEqual(provider.calls, 0)
                    finally:
                        await client.put("/api/profile", json={"preferred_name": before})

            asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
