"""J55 — couche voix 100 % locale, honnête quand rien n'est disponible.

TDD : tests écrits avant src/local_voice.py. Aucun appel OS réel dans les tests.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))


class LocalVoiceTest(unittest.TestCase):
    def test_probe_without_engine_is_honest(self):
        import local_voice

        with patch.object(local_voice, "_sapi_available", return_value=False), \
             patch.object(local_voice, "_stt_available", return_value=False):
            result = local_voice.probe()
        self.assertFalse(result["available"])
        self.assertEqual(result["mode"], "no_local_voice")
        self.assertEqual(result["reason"], "no_local_voice")

    def test_probe_with_sapi_is_offline(self):
        import local_voice

        with patch.object(local_voice, "_sapi_available", return_value=True), \
             patch.object(local_voice, "_stt_available", return_value=False):
            result = local_voice.probe()
        self.assertTrue(result["available"])
        self.assertEqual(result["mode"], "offline")
        self.assertTrue(result["tts"])
        self.assertFalse(result["stt"])

    def test_speak_refuses_when_no_engine(self):
        import local_voice

        with patch.object(local_voice, "_sapi_available", return_value=False):
            result = local_voice.speak("salam")
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "no_local_voice")

    def test_speak_uses_sapi_and_escapes_quotes(self):
        import local_voice

        seen = {}

        def fake_run(command, **kwargs):
            seen["command"] = command
            return True, ""

        with patch.object(local_voice, "_sapi_available", return_value=True), \
             patch.object(local_voice, "_run_powershell", side_effect=fake_run):
            result = local_voice.speak("it's ok")

        self.assertTrue(result["ok"])
        self.assertEqual(result["engine"], "sapi_tts")
        self.assertIn("it''s ok", seen["command"])
        self.assertIn("System.Speech", seen["command"])

    def test_speak_allows_a_long_local_utterance(self):
        import local_voice

        seen = {}

        def fake_run(command, **kwargs):
            seen.update(kwargs)
            return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

        with patch.object(local_voice, "_sapi_available", return_value=True), \
             patch.object(local_voice.subprocess, "run", side_effect=fake_run):
            result = local_voice.speak("test")
        self.assertTrue(result["ok"])
        self.assertGreaterEqual(seen.get("timeout", 0), 30)

    def test_listen_is_never_silent_about_missing_stt(self):
        import local_voice

        with patch.object(local_voice.local_stt, "_engine_available",
                          return_value=False):
            result = local_voice.listen()
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "no_local_stt")
        self.assertEqual(result["text"], "")

    def test_no_secret_field_in_capabilities(self):
        import json

        import local_voice

        with patch.object(local_voice, "_sapi_available", return_value=True), \
             patch.object(local_voice, "_stt_available", return_value=True):
            payload = json.dumps(local_voice.probe())
        for word in ("key", "token", "password", "secret"):
            self.assertNotIn(word, payload.lower())


class SentenceSplittingTest(unittest.TestCase):
    def test_split_ready_keeps_sentence_boundaries(self):
        import local_voice

        chunks = local_voice.split_ready("Salam. Comment ça va? Bien!\n\nAu revoir.")
        self.assertEqual(chunks, ["Salam.", "Comment ça va?", "Bien!", "Au revoir."])

    def test_split_ready_skips_empty_and_bounds_length(self):
        import local_voice

        self.assertEqual(local_voice.split_ready("   \n  "), [])
        long_one = local_voice.split_ready("mot " * 120)
        self.assertTrue(long_one)
        self.assertTrue(all(0 < len(chunk) <= local_voice.MAX_CHUNK_CHARS for chunk in long_one))

    def test_speak_can_stop_between_sentences(self):
        import local_voice

        seen = []

        def fake_run(command, **kwargs):
            seen.append(command)
            return True, ""

        calls = {"n": 0}

        def stop_after_one():
            calls["n"] += 1
            return calls["n"] >= 1

        with patch.object(local_voice, "_sapi_available", return_value=True), \
             patch.object(local_voice, "_run_powershell", side_effect=fake_run):
            result = local_voice.speak("Un. Deux. Trois.", stop_fn=stop_after_one)
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "barge_in")
        self.assertEqual(len(seen), 1)


if __name__ == "__main__":
    unittest.main()
