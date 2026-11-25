"""/api/health must only call vision_ready for a local vision model."""
from __future__ import annotations

import asyncio
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


class StubProvider:
    name = "health test"
    model = "stub"

    async def complete(self, _messages: list[Message]) -> str:
        return ""

    async def stream(self, _messages: list[Message]):
        yield ""


class HealthLocalOnlyTest(unittest.TestCase):
    def _vision_ready(self, provider: str, *, with_mmproj: bool, cloud_model: str) -> bool:
        with TemporaryDirectory(prefix="atulya-health-", dir=Path.cwd()) as tmp:
            root = Path(tmp)
            models = root / "models"
            models.mkdir()
            if with_mmproj:
                vision = models / "vision"
                vision.mkdir()
                (vision / "mmproj-Qwen_Qwen3.5-2B-bf16.gguf").write_bytes(b"local-only")
            settings = Settings(
                assistant_name="Atulya", host="127.0.0.1", port=8501,
                data_dir=root / "data", models_dir=models,
                model_provider=provider, model_name="", model_base_url="", model_api_key="",
            )
            with patch.dict(os.environ, {"ATULYA_OPENROUTER_MODEL": cloud_model}), \
                 patch.object(server, "_make_brain", lambda _settings: Brain(StubProvider(), assistant_name="Atulya")):
                app = server.create_app(settings)

            async def probe() -> bool:
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                             base_url="http://localhost") as client:
                    response = await client.get("/api/health")
                    self.assertEqual(response.status_code, 200)
                    return bool(response.json()["vision_ready"])

            return asyncio.run(probe())

    def test_cloud_provider_names_never_enable_vision(self) -> None:
        self.assertFalse(self._vision_ready(
            "gemini", with_mmproj=False, cloud_model="gemini-2.5-vision"))
        self.assertFalse(self._vision_ready(
            "openrouter", with_mmproj=False, cloud_model="google/gemini-2.5-pro-vision"))

    def test_only_a_local_mmproj_enables_vision(self) -> None:
        self.assertFalse(self._vision_ready(
            "local", with_mmproj=False, cloud_model=""))
        self.assertTrue(self._vision_ready(
            "local", with_mmproj=True, cloud_model=""))


if __name__ == "__main__":
    unittest.main()
