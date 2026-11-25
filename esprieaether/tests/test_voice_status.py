"""J64 — état vocal temps réel pour animer le visage, sans secret.

TDD rouge : ces tests précèdent src/voice_status.py. Aucun micro, TTS ou
réseau réel ; tout est écrit dans un dossier temporaire.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))


class VoiceStatusTest(unittest.TestCase):
    def test_write_is_atomic_and_stage_is_bounded(self):
        import voice_status

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "voice_status.json"
            payload = voice_status.write(
                "speaking", level=2.5, reason="api_key=hunter2", path=path
            )
            raw = path.read_text(encoding="utf-8")
            self.assertEqual(payload["stage"], "speaking")
            self.assertEqual(payload["level"], 1.0)
            self.assertIn("updatedAt", payload)
            self.assertEqual(json.loads(raw)["stage"], "speaking")
            self.assertNotIn("hunter2", raw)
            self.assertEqual(list(Path(tmp).rglob(".*")), [])

    def test_unknown_stage_falls_back_to_idle(self):
        import voice_status

        with tempfile.TemporaryDirectory() as tmp:
            payload = voice_status.write("dancing", path=Path(tmp) / "s.json")
        self.assertEqual(payload["stage"], "idle")

    def test_read_is_honest_when_file_is_absent_or_corrupt(self):
        import voice_status

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "absent.json"
            self.assertEqual(voice_status.read(path)["stage"], "idle")
            path.write_text("{bad json", encoding="utf-8")
            self.assertEqual(voice_status.read(path)["reason"], "no_data_source")
            path.write_text(json.dumps({"stage": "evil", "level": 9}), encoding="utf-8")
            self.assertEqual(voice_status.read(path)["stage"], "idle")

    def test_status_never_exposes_secret_field_names(self):
        import voice_status

        with tempfile.TemporaryDirectory() as tmp:
            payload = voice_status.write("idle", path=Path(tmp) / "s.json")
        blob = json.dumps(payload, ensure_ascii=False).lower()
        for word in ("api_key", "token", "password", "authorization"):
            self.assertNotIn(word, blob)


if __name__ == "__main__":
    unittest.main()
