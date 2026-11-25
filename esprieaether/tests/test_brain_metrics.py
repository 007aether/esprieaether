"""J76/D2 — mesure réelle et bornée du cerveau local, sans chiffre inventé."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
        self.status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class FakeStore:
    def __init__(self):
        self.rows = []

    def record(self, action, actor="", detail=""):
        self.rows.append({"action": action, "status": "running"})
        return 1

    def update(self, run_id, status, detail=""):
        self.rows[-1].update({"status": status, "detail": detail})


class BrainMetricsTest(unittest.TestCase):
    def test_reply_records_real_elapsed_and_completion_tokens(self):
        import voice_loop

        payload = {
            "choices": [{"message": {"content": "wa 3laykom"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 30, "total_tokens": 40},
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "brain_metrics.json"
            writer = lambda metrics: voice_loop.write_brain_metrics(metrics, path)
            with patch.object(voice_loop, "_store", return_value=FakeStore()), \
                 patch.object(voice_loop.time, "monotonic", side_effect=[100.0, 100.2]), \
                 patch.object(voice_loop.urllib.request, "urlopen",
                              return_value=FakeResponse(payload)):
                result = voice_loop.brain_reply("salam", metrics_fn=writer)
            saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(result["ok"])
        self.assertEqual(result["elapsedMs"], 200)
        self.assertEqual(result["tokensPerSecond"], 150.0)
        self.assertEqual(saved["tokensPerSecond"], 150.0)
        self.assertTrue(saved["available"])
        self.assertNotIn("api_key", json.dumps(saved).lower())

    def test_missing_usage_is_honest(self):
        import voice_loop

        payload = {"choices": [{"message": {"content": "salam"}}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "brain_metrics.json"
            writer = lambda metrics: voice_loop.write_brain_metrics(metrics, path)
            with patch.object(voice_loop, "_store", return_value=FakeStore()), \
                 patch.object(voice_loop.time, "monotonic", side_effect=[1.0, 1.05]), \
                 patch.object(voice_loop.urllib.request, "urlopen",
                              return_value=FakeResponse(payload)):
                result = voice_loop.brain_reply("salam", metrics_fn=writer)
            saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(result["ok"])
        self.assertIsNone(result["tokensPerSecond"])
        self.assertFalse(saved["available"])
        self.assertEqual(saved["reason"], "no_usage_data")


if __name__ == "__main__":
    unittest.main()
