"""J174 — le pont OpenCode passe par /api/chat sans jamais appeler le modèle."""
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
        raise AssertionError("cette phrase déterministe ne doit pas atteindre le modèle")

    async def complete(self, messages: list[Message]) -> str:
        self._unexpected(messages)
        return ""

    async def stream(self, messages: list[Message]):
        self._unexpected(messages)
        yield ""


class LocalBridgeFlowTest(unittest.TestCase):
    def test_chat_ecrit_et_relit_le_pont_sans_modele(self) -> None:
        with TemporaryDirectory(prefix="atulya-bridge-e2e-", dir=Path.cwd()) as tmp:
            root = Path(tmp)
            models = root / "models"
            models.mkdir()
            shared = root / "shared"
            settings = Settings(
                assistant_name="Atulya", host="127.0.0.1", port=8501,
                data_dir=root / "data", models_dir=models,
                model_provider="", model_name="", model_base_url="", model_api_key="",
            )
            provider = NoModelProvider()
            with patch.object(server, "_make_brain", lambda _settings: Brain(provider, assistant_name="Atulya")):
                app = server.create_app(settings)

            async def exercise() -> None:
                transport = httpx.ASGITransport(app=app)
                with patch.dict(os.environ, {"ATULYA_OPENCODE_BRIDGE_DIR": str(shared)}):
                    async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
                        token = app.state.auth_store.create_session("admin")
                        client.cookies.set("atulya_session", token)

                        who = await client.post("/api/chat", json={
                            "messages": [{"role": "user", "content": "من أنت؟"}]})
                        self.assertEqual(who.status_code, 200, who.text)
                        self.assertEqual(who.json()["route"], "local_bridge")
                        self.assertIn("أتوليا", who.json()["text"])

                        ask = await client.post("/api/chat", json={
                            "messages": [{"role": "user", "content": "سول أوبن كود: واش كاين خدمة؟"}]})
                        self.assertEqual(ask.json()["route"], "local_bridge")
                        row = json.loads((shared / "questions.jsonl").read_text(encoding="utf-8").splitlines()[-1])
                        self.assertEqual(row["status"], "pending")
                        self.assertEqual(row["id"] in ask.json()["text"], True)

                        (shared / "answers.jsonl").write_text(
                            json.dumps({"kind": "answer", "question_id": row["id"],
                                        "text": "الجواب المسجّل من OpenCode."}, ensure_ascii=False) + "\n",
                            encoding="utf-8")
                        read = await client.post("/api/chat", json={
                            "messages": [{"role": "user", "content": "شنو قال أوبن كود؟"}]})
                        self.assertEqual(read.json()["text"], "الجواب المسجّل من OpenCode.")

                        catalog = await client.post("/api/chat", json={
                            "messages": [{"role": "user", "content": "عطيني المشاريع"}]})
                        self.assertEqual(catalog.json()["route"], "github_catalog")
                        self.assertIn("50 المشاريع", catalog.json()["text"])

                        knowledge = await client.post("/api/chat", json={
                            "messages": [{"role": "user", "content": "CHENO LMA3RIFA LI 3ANDAK"}]})
                        self.assertEqual(knowledge.json()["route"], "local_bridge")
                        self.assertIn("كاتالوج", knowledge.json()["text"])

                        unified = await client.post("/api/chat", json={
                            "messages": [{"role": "user", "content": "chi projet ijema33 kolechi widifo l esprieaether"}]})
                        self.assertEqual(unified.json()["route"], "github_catalog")
                        self.assertIn("affaan-m/ECC", unified.json()["text"])
                        self.assertEqual(provider.calls, 0)

            asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
