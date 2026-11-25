"""J62 — صوت دايم (مايكروفون → دماغ → سبيكرات) + صندوق نصي للقراءة.

TDD: الاختبارات قبل src/voice_inbox.py و voice_daemon.py. أي ميكروفون أو
TTS أو نوم كيتدارو بـ mock؛ ما كاينش TODO حقيقي فالاختبارات.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))


class FakeInbox:
    def __init__(self):
        self.rows = []

    def append(self, record):
        self.rows.append(dict(record))
        return dict(record)

    def read(self, limit=20):
        return self.rows[-limit:]


class VoiceInboxTest(unittest.TestCase):
    def test_append_redacts_secrets_and_reads_back(self):
        import voice_inbox

        with tempfile.TemporaryDirectory() as tmp:
            inbox = voice_inbox.VoiceInbox(Path(tmp) / "voice.jsonl",
                                           Path(tmp) / "latest.txt")
            inbox.append({"ok": True, "heard": "TOKEN=abc123",
                          "reply": "salam", "spoken": True, "language": "ar"})
            rows = inbox.read()
            latest = (Path(tmp) / "latest.txt").read_text(encoding="utf-8")
        self.assertEqual(len(rows), 1)
        blob = json.dumps(rows, ensure_ascii=False) + latest
        self.assertNotIn("abc123", blob)
        self.assertEqual(rows[0]["heard"], "TOKEN=<redacted>")

    def test_read_skips_corrupt_lines(self):
        import voice_inbox

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "voice.jsonl"
            path.write_text('{"ok": true, "heard": "salam"}\n{bad json}\n',
                            encoding="utf-8")
            rows = voice_inbox.VoiceInbox(path, Path(tmp) / "latest.txt").read()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["heard"], "salam")

    def test_inbox_never_stores_keys_or_tokens_as_fields(self):
        import voice_inbox

        self.assertTrue(voice_inbox.probe())
        blob = json.dumps(voice_inbox.probe(), ensure_ascii=False).lower()
        for word in ("api_key", "token", "password", "authorization"):
            self.assertNotIn(word, blob)


class VoiceDaemonTest(unittest.TestCase):
    def test_mic_monitor_callback_reads_multichannel_frames(self):
        import numpy as np
        import sounddevice as sd
        import voice_daemon

        captured = {}

        class FakeStream:
            def __init__(self, **kwargs):
                captured["callback"] = kwargs["callback"]

            def start(self):
                pass

            def stop(self):
                pass

            def close(self):
                pass

        with patch.object(sd, "InputStream", FakeStream):
            self.assertTrue(voice_daemon.MicEnergyMonitor().start())
        frames = np.array([[0.5, -0.5], [0.5, -0.5]], dtype=np.float32)
        captured["callback"](frames, 2, None, None)
        self.assertAlmostEqual(voice_daemon._mic_level(), 0.5, places=5)

    def test_once_writes_inbox_and_returns_full_turn(self):
        import voice_daemon

        inbox = FakeInbox()
        turn = {"ok": True, "heard": "salam", "reply": "wa 3laykom",
                "spoken": True, "language": "ar", "engine": "local-brain",
                "model": "dolphin3", "reason": None}
        with patch.object(voice_daemon, "_inbox", return_value=inbox), \
             patch.object(voice_daemon.voice_loop, "voice_turn", return_value=turn):
            result = voice_daemon.once()
        self.assertTrue(result["ok"])
        self.assertEqual(inbox.rows[0]["heard"], "salam")
        self.assertEqual(inbox.rows[0]["reply"], "wa 3laykom")
        self.assertTrue(inbox.rows[0]["spoken"])

    def test_failed_turn_is_recorded_honestly(self):
        import voice_daemon

        inbox = FakeInbox()
        failure = {"ok": False, "heard": "", "reply": "", "spoken": False,
                   "reason": "mic_unavailable:OSError"}
        with patch.object(voice_daemon, "_inbox", return_value=inbox), \
             patch.object(voice_daemon.voice_loop, "voice_turn", return_value=failure):
            result = voice_daemon.once()
        self.assertFalse(result["ok"])
        self.assertIn("mic_unavailable", result["reason"])
        self.assertEqual(inbox.rows[-1]["ok"], False)

    def test_echo_of_own_speech_is_suppressed(self):
        import voice_daemon

        inbox = FakeInbox()
        voice_daemon._last_spoken["text"] = "Alright, let's get this conversation going!"
        voice_daemon._last_spoken["ts"] = __import__("time").monotonic()
        heard = {"ok": True, "text": "Alright, let's get this conversation going.",
                 "language": "en"}
        with patch.object(voice_daemon, "_inbox", return_value=inbox), \
             patch.object(voice_daemon.local_voice, "listen", return_value=heard), \
             patch.object(voice_daemon.voice_loop, "brain_reply",
                          side_effect=AssertionError("must not reply to own voice")):
            result = voice_daemon.once()
        self.assertFalse(result["ok"])
        self.assertIn("echo_suppressed", result["reason"])
        self.assertEqual(inbox.rows[-1]["ok"], False)

    def test_successful_turn_remembers_spoken_reply(self):
        import voice_daemon

        inbox = FakeInbox()
        voice_daemon._last_spoken["text"] = ""
        turn = {"ok": True, "heard": "salam", "reply": "wa 3laykom",
                "spoken": True, "reason": None}
        with patch.object(voice_daemon, "_inbox", return_value=inbox), \
             patch.object(voice_daemon.voice_loop, "voice_turn", return_value=turn):
            voice_daemon.once()
        self.assertEqual(voice_daemon._last_spoken["text"], "wa 3laykom")

    def test_once_publishes_live_stage_for_the_face(self):
        import voice_daemon

        inbox = FakeInbox()
        turn = {"ok": True, "heard": "salam", "reply": "wa 3laykom",
                "spoken": True, "reason": None}
        with patch.object(voice_daemon, "_inbox", return_value=inbox), \
             patch.object(voice_daemon.voice_loop, "voice_turn", return_value=turn), \
             patch.object(voice_daemon.voice_status, "write") as write:
            voice_daemon.once()
        stages = [call.args[0] for call in write.call_args_list]
        self.assertIn("listening", stages)
        self.assertEqual(stages[-1], "idle")

    def test_failed_turn_publishes_honest_idle_reason(self):
        import voice_daemon

        failure = {"ok": False, "reason": "listen:mic_unavailable", "spoken": False}
        with patch.object(voice_daemon, "_inbox", return_value=FakeInbox()), \
             patch.object(voice_daemon.voice_loop, "voice_turn", return_value=failure), \
             patch.object(voice_daemon.voice_status, "write") as write:
            voice_daemon.once()
        last = write.call_args_list[-1]
        self.assertEqual(last.args[0], "idle")
        self.assertIn("mic_unavailable", str(last.args[2]))

    def test_darija_language_maps_to_ar_and_auto_stays_none(self):
        import importlib

        import voice_daemon

        with patch.dict("os.environ", {"SUNNAVOK_VOICE_LANGUAGE": "darija"}):
            self.assertEqual(importlib.reload(voice_daemon).LANGUAGE, "ar")
        with patch.dict("os.environ", {"SUNNAVOK_VOICE_LANGUAGE": "auto"}):
            self.assertIsNone(importlib.reload(voice_daemon).LANGUAGE)
        with patch.dict("os.environ", {}, clear=True):
            importlib.reload(voice_daemon)

    def test_mic_monitor_resets_after_own_speech(self):
        import time

        import voice_daemon

        monitor = voice_daemon.MicEnergyMonitor(threshold=0.5)
        with patch.object(voice_daemon, "_mic_level", return_value=0.9):
            monitor.suppress(seconds=30)
            self.assertFalse(monitor.triggered())
            monitor.reset()
            self.assertTrue(monitor.triggered())
        self.assertGreater(time.monotonic(), 0)

    def test_barge_in_turn_clears_own_voice_memory(self):
        import voice_daemon

        inbox = FakeInbox()
        voice_daemon._last_spoken["text"] = "ma voix"
        voice_daemon._last_spoken["ts"] = __import__("time").monotonic()

        def fake_turn(**kwargs):
            self.assertTrue(callable(kwargs.get("cancel_fn")), "cancel_fn absent")
            return {"ok": False, "spoken": False, "reason": "barge_in"}

        monitor = voice_daemon.MicEnergyMonitor(threshold=0.5)
        with patch.object(voice_daemon, "_inbox", return_value=inbox), \
             patch.object(voice_daemon.voice_loop, "voice_turn", side_effect=fake_turn):
            result = voice_daemon.once(barge_monitor=monitor)
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "barge_in")
        self.assertEqual(inbox.rows[-1]["reason"], "barge_in")
        self.assertEqual(voice_daemon._last_spoken["text"], "")

    def test_probe_reports_local_loop_without_secret_fields(self):
        import voice_daemon

        payload = voice_daemon.probe()
        self.assertIn("mode", payload)
        blob = json.dumps(payload, ensure_ascii=False).lower()
        for word in ("api_key", "token", "password", "authorization"):
            self.assertNotIn(word, blob)

    def test_main_refuses_second_instance(self):
        import voice_daemon

        fake_lock = SimpleNamespace(acquire=lambda: False, release=lambda: None)
        with patch.object(voice_daemon, "SingletonLock", return_value=fake_lock), \
             patch.object(voice_daemon.logger, "info") as info:
            voice_daemon.main()
        messages = " ".join(str(c) for c in info.call_args_list)
        self.assertIn("another instance", messages)


if __name__ == "__main__":
    unittest.main()
