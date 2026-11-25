"""J57 — STT محلي حقيقي (Whisper عبر faster-whisper)، بلا clé وبلا سحاب.

TDD : الاختبارات مكتوبة قبل src/local_stt.py. أي مكالمة mic أو نموذج
تُMockː ما كاينش TODO حقيقي فالاختبارات.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))


class LocalSttTest(unittest.TestCase):
    def test_probe_is_honest_without_engine(self):
        import local_stt

        with patch.object(local_stt, "_engine_available", return_value=False):
            result = local_stt.probe()
        self.assertFalse(result["available"])
        self.assertEqual(result["mode"], "no_local_stt")
        self.assertEqual(result["reason"], "engine_not_installed")

    def test_probe_reports_local_engine_when_installed(self):
        import local_stt

        fake = object()
        with patch.object(local_stt, "_engine_available", return_value=True), \
             patch.object(local_stt, "_get_model", return_value=fake):
            result = local_stt.probe()
        self.assertTrue(result["available"])
        self.assertEqual(result["mode"], "local_whisper")
        self.assertEqual(result["engine"], "faster-whisper")
        self.assertTrue(result["model"])

    def test_model_dir_is_inside_project(self):
        import local_stt

        assert local_stt.MODEL_DIR.is_absolute()
        self.assertTrue(
            local_stt.MODEL_DIR.is_relative_to(BASE_DIR.parent),
            "le modèle doit rester dans SUNNAVOK/models/stt",
        )
        self.assertIn("models", local_stt.MODEL_DIR.parts)

    def test_transcribe_file_rejects_missing_file(self):
        import local_stt

        result = local_stt.transcribe_file(str(BASE_DIR / "state" / "absent.wav"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "file_not_found")

    def test_transcribe_file_joins_segments_and_detects_language(self):
        import local_stt

        class Segment:
            def __init__(self, text):
                self.text = text

        class FakeModel:
            def transcribe(self, path, language=None, vad_filter=True):
                self.kwargs = {"language": language, "vad_filter": vad_filter}
                return ([Segment(" salaam "), Segment("3laykom")],
                        type("Info", (), {"language": "ar"})())

        model = FakeModel()
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "a.wav"
            wav.write_bytes(b"RIFF")
            with patch.object(local_stt, "_engine_available", return_value=True), \
                 patch.object(local_stt, "_get_model", return_value=model):
                result = local_stt.transcribe_file(str(wav), language="ar")
        self.assertTrue(result["ok"])
        self.assertEqual(result["text"], "salaam 3laykom")
        self.assertEqual(result["language"], "ar")
        self.assertEqual(result["engine"], "faster-whisper")
        self.assertTrue(model.kwargs["vad_filter"])

    def test_transcribe_failure_is_reported_not_faked(self):
        import local_stt

        class Broken:
            def transcribe(self, *a, **k):
                raise RuntimeError("decode failed")

        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "a.wav"
            wav.write_bytes(b"RIFF")
            with patch.object(local_stt, "_engine_available", return_value=True), \
                 patch.object(local_stt, "_get_model", return_value=Broken()):
                result = local_stt.transcribe_file(str(wav))
        self.assertFalse(result["ok"])
        self.assertIn("decode failed", result["reason"])

    def test_record_and_transcribe_uses_local_mic_then_local_model(self):
        import local_stt

        calls = {}

        def fake_record(path, seconds):
            calls["record"] = (path, seconds)
            Path(path).write_bytes(b"RIFF")

        with patch.object(local_stt, "_engine_available", return_value=True), \
             patch.object(local_stt, "_record_wav", side_effect=fake_record), \
             patch.object(local_stt, "transcribe_file",
                          return_value={"ok": True, "text": "salam", "language": "ar",
                                        "engine": "faster-whisper", "reason": None}):
            result = local_stt.record_and_transcribe(seconds=2, language="ar")
        self.assertTrue(result["ok"])
        self.assertEqual(result["text"], "salam")
        self.assertEqual(result["audioSeconds"], 2)
        self.assertTrue(str(calls["record"][0]).endswith(".wav"))

    def test_model_loads_offline_when_cached(self):
        import local_stt

        calls = {}

        class FakeModel:
            def __init__(self, name, **kwargs):
                calls.update(kwargs)

        with patch.object(local_stt, "_MODEL", None), \
             patch.object(local_stt, "_model_cached", return_value=True), \
             patch("faster_whisper.WhisperModel", FakeModel):
            local_stt._get_model()
        self.assertTrue(calls.get("local_files_only"), "لا طلبات سحاب عند البداية الباردة")
        self.assertEqual(calls.get("device"), "cpu")
        self.assertEqual(calls.get("compute_type"), "int8")

    def test_first_download_still_possible_when_not_cached(self):
        import local_stt

        calls = {}

        class FakeModel:
            def __init__(self, name, **kwargs):
                calls.update(kwargs)

        with patch.object(local_stt, "_MODEL", None), \
             patch.object(local_stt, "_model_cached", return_value=False), \
             patch("faster_whisper.WhisperModel", FakeModel):
            local_stt._get_model()
        self.assertFalse(calls.get("local_files_only"))

    def test_no_secret_field_in_payloads(self):
        import local_stt

        with patch.object(local_stt, "_engine_available", return_value=False):
            payload = json.dumps({"probe": local_stt.probe(),
                                  "transcribe": local_stt.transcribe_file("no.wav")})
        for word in ("api_key", "token", "password", "secret"):
            self.assertNotIn(word, payload.lower())

    def test_voice_facade_delegates_to_real_stt(self):
        import local_voice

        fake = {"ok": True, "text": "salam", "language": "ar",
                "engine": "faster-whisper", "reason": None, "audioSeconds": 3}
        with patch.object(local_voice.local_stt, "record_and_transcribe",
                          return_value=fake) as mocked:
            result = local_voice.listen(seconds=3, language="ar")
        self.assertTrue(result["ok"])
        self.assertEqual(result["text"], "salam")
        mocked.assert_called_once_with(seconds=3, language="ar")

    def test_voice_facade_is_honest_when_engine_absent(self):
        import local_voice

        with patch.object(local_voice.local_stt, "_engine_available",
                          return_value=False):
            result = local_voice.listen()
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "no_local_stt")
        self.assertEqual(result["text"], "")


if __name__ == "__main__":
    unittest.main()
