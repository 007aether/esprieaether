"""J58 — سلسلة الصوت الكاملة: ميكروفون → Whisper → دماغ :31416 → SAPI.

TDD: الاختبارات مكتوبة قبل src/voice_loop.py. أي ميكروفون، شبكة أو TTS
كايتدارو بـ mock؛ ما كاينش TODO حقيقي فالاختبارات.
"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))


class FakeStore:
    def __init__(self):
        self.rows = []

    def record(self, action, **kwargs):
        rid = len(self.rows) + 1
        self.rows.append({"id": rid, "action": action, "status": "running",
                          "detail": kwargs.get("detail", "")})
        return rid

    def update(self, rid, status, detail=None):
        for row in self.rows:
            if row["id"] == rid:
                row["status"] = status
                if detail is not None:
                    row["detail"] = detail
                return True
        return False


def fake_urlopen(payload):
    class Response:
        def read(self):
            return json.dumps(payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    return Response()


class VoiceLoopTest(unittest.TestCase):
    def test_brain_reply_parses_local_model_without_key(self):
        import voice_loop

        calls = {}
        payload = {"choices": [{"message": {"content": "salam 3laykom"}}]}

        def fake_request(req, timeout=None):
            calls["headers"] = dict(req.header_items())
            calls["timeout"] = timeout
            calls["url"] = req.full_url
            return fake_urlopen(payload)

        with patch.object(voice_loop.urllib.request, "urlopen", side_effect=fake_request), \
             patch.object(voice_loop, "_store", return_value=FakeStore()):
            result = voice_loop.brain_reply("ki dayra?", model="dolphin3")
        self.assertTrue(result["ok"])
        self.assertEqual(result["text"], "salam 3laykom")
        self.assertEqual(result["model"], "dolphin3")
        self.assertEqual(calls["url"], voice_loop.BRAIN_URL)
        for key in calls["headers"]:
            self.assertNotIn("author", key.lower())
            self.assertNotIn("key", key.lower())

    def test_brain_reply_system_prompt_asks_for_darija(self):
        import voice_loop

        bodies = []

        def fake_request(req, timeout=None):
            bodies.append(json.loads(req.data.decode("utf-8")))
            return fake_urlopen({"choices": [{"message": {"content": "salam"}}]})

        with patch.object(voice_loop.urllib.request, "urlopen", side_effect=fake_request), \
             patch.object(voice_loop, "_store", return_value=FakeStore()):
            voice_loop.brain_reply("kifach ndir?")
        prompt = bodies[0]["messages"][0]["content"].lower()
        self.assertIn("darija", prompt)
        self.assertIn("marocain", prompt)
        self.assertIn("lettres arabes", prompt)
        self.assertIn("aucune lettre latine", prompt)
        self.assertIn("approbation", prompt)

    def test_brain_reply_asks_for_a_short_spoken_answer(self):
        import voice_loop

        bodies = []

        def fake_request(req, timeout=None):
            bodies.append(json.loads(req.data.decode("utf-8")))
            return fake_urlopen({"choices": [{"message": {"content": "ok"}}]})

        with patch.object(voice_loop.urllib.request, "urlopen", side_effect=fake_request), \
             patch.object(voice_loop, "_store", return_value=FakeStore()):
            voice_loop.brain_reply("salam")
        body = bodies[0]
        self.assertEqual(body["messages"][0]["role"], "system")
        self.assertLessEqual(body["max_tokens"], 150)

    def test_brain_reply_is_honest_on_http_error(self):
        import urllib.error

        import voice_loop

        with patch.object(voice_loop.urllib.request, "urlopen",
                          side_effect=urllib.error.HTTPError("u", 503, "down", None, None)), \
             patch.object(voice_loop, "_store", return_value=FakeStore()):
            result = voice_loop.brain_reply("test")
        self.assertFalse(result["ok"])
        self.assertIn("503", result["reason"])

    def test_brain_reply_refuses_when_gate_denies(self):
        import voice_loop

        denied = type("D", (), {"allowed": False, "reason": "private_network"})()
        with patch.object(voice_loop, "decide", return_value=denied), \
             patch.object(voice_loop.urllib.request, "urlopen",
                          side_effect=AssertionError("must not call")), \
             patch.object(voice_loop, "_store", return_value=FakeStore()):
            result = voice_loop.brain_reply("test")
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "gate_denied:private_network")

    def test_voice_turn_full_chain_with_terminal_ledger(self):
        import voice_loop

        store = FakeStore()
        heard = {"ok": True, "text": "salam", "language": "ar", "engine": "faster-whisper"}
        brain = {"ok": True, "text": "wa 3laykom s-salam", "model": "dolphin3", "engine": "local-brain"}
        spoken = {"ok": True, "engine": "sapi_tts"}

        with patch.object(voice_loop.local_voice, "listen", return_value=heard), \
             patch.object(voice_loop, "brain_reply", return_value=brain), \
             patch.object(voice_loop.local_voice, "speak", return_value=spoken), \
             patch.object(voice_loop, "_store", return_value=store):
            result = voice_loop.voice_turn(seconds=3, language="ar")
        self.assertTrue(result["ok"])
        self.assertEqual(result["heard"], "salam")
        self.assertEqual(result["reply"], "wa 3laykom s-salam")
        self.assertTrue(result["spoken"])
        self.assertEqual([r["action"] for r in store.rows], ["voice_turn"])
        self.assertTrue(all(r["status"] == "succeeded" for r in store.rows))

    def test_voice_turn_accepts_an_injected_listener(self):
        import voice_loop

        heard = {"ok": True, "text": "salam", "language": "ar"}
        brain = {"ok": True, "text": "wa 3laykom", "model": "dolphin3"}
        listener = Mock(return_value=heard)
        with patch.object(voice_loop.local_voice, "listen",
                          side_effect=AssertionError("must use injected listener")), \
             patch.object(voice_loop, "brain_reply", return_value=brain), \
             patch.object(voice_loop.local_voice, "speak", return_value={"ok": True}), \
             patch.object(voice_loop, "_store", return_value=FakeStore()):
            result = voice_loop.voice_turn(listen_fn=listener)
        self.assertTrue(result["ok"])
        listener.assert_called_once()

    def test_voice_turn_emits_stage_sequence_for_the_face(self):
        import voice_loop

        heard = {"ok": True, "text": "salam", "language": "ar"}
        brain = {"ok": True, "text": "wa 3laykom", "model": "dolphin3"}
        stages = []

        def status(stage, level=0.0, reason=None):
            stages.append((stage, level, reason))

        with patch.object(voice_loop.local_voice, "listen", return_value=heard), \
             patch.object(voice_loop, "brain_reply", return_value=brain), \
             patch.object(voice_loop.local_voice, "speak", return_value={"ok": True}), \
             patch.object(voice_loop, "_store", return_value=FakeStore()):
            result = voice_loop.voice_turn(status_fn=status)

        self.assertTrue(result["ok"])
        names = [item[0] for item in stages]
        self.assertEqual(names, ["listening", "thinking", "speaking", "idle"])
        self.assertGreater(stages[2][1], 0)
        self.assertTrue(all(round(item[1], 2) == item[1] for item in stages))

    def test_voice_turn_stage_failure_is_honest(self):
        import voice_loop

        stages = []
        with patch.object(voice_loop.local_voice, "listen",
                          return_value={"ok": False, "reason": "mic_unavailable"}), \
             patch.object(voice_loop, "_store", return_value=FakeStore()):
            result = voice_loop.voice_turn(status_fn=lambda *a: stages.append(a))
        self.assertFalse(result["ok"])
        self.assertEqual(stages[-1][0], "idle")
        self.assertEqual(stages[-1][2], "listen:mic_unavailable")

    def test_voice_turn_stops_honestly_when_mic_fails(self):
        import voice_loop

        store = FakeStore()
        with patch.object(voice_loop.local_voice, "listen",
                          return_value={"ok": False, "text": "", "reason": "mic_unavailable:OSError"}), \
             patch.object(voice_loop, "brain_reply",
                          side_effect=AssertionError("must not call")), \
             patch.object(voice_loop.local_voice, "speak",
                          side_effect=AssertionError("must not call")), \
             patch.object(voice_loop, "_store", return_value=store):
            result = voice_loop.voice_turn()
        self.assertFalse(result["ok"])
        self.assertIn("mic_unavailable", result["reason"])
        self.assertEqual(store.rows[-1]["status"], "failed")

    def test_voice_turn_ledger_never_contains_spoken_text(self):
        import voice_loop

        store = FakeStore()
        heard = {"ok": True, "text": "SERCRET_MOT_DE_PASSE=abc123", "language": "en"}
        brain = {"ok": True, "text": "réponse", "model": "dolphin3"}
        with patch.object(voice_loop.local_voice, "listen", return_value=heard), \
             patch.object(voice_loop, "brain_reply", return_value=brain), \
             patch.object(voice_loop, "_store", return_value=store):
            voice_loop.voice_turn(speak_reply=False)
        blob = json.dumps(store.rows, ensure_ascii=False)
        self.assertNotIn("abc123", blob)

    def test_long_reply_is_shortened_before_speaking(self):
        import voice_loop

        long_reply = "x" * 500
        heard = {"ok": True, "text": "salam", "language": "ar"}
        brain = {"ok": True, "text": long_reply, "model": "dolphin3"}
        with patch.object(voice_loop.local_voice, "listen", return_value=heard), \
             patch.object(voice_loop, "brain_reply", return_value=brain), \
             patch.object(voice_loop.local_voice, "speak",
                          return_value={"ok": True}) as spoken, \
             patch.object(voice_loop, "_store", return_value=FakeStore()):
            result = voice_loop.voice_turn()
        self.assertEqual(result["reply"], long_reply)
        self.assertLessEqual(len(spoken.call_args[0][0]), 240)

    def test_payloads_have_no_secret_field(self):
        import voice_loop

        self.assertTrue(voice_loop.probe())
        blob = json.dumps(voice_loop.probe(), ensure_ascii=False).lower()
        for word in ("api_key", "token", "password", "authorization"):
            self.assertNotIn(word, blob)


    def test_cancel_fn_stops_before_brain_replies(self):
        import voice_loop

        heard = {"ok": True, "text": "salam", "language": "ar"}
        stages = []
        with patch.object(voice_loop.local_voice, "listen", return_value=heard), \
             patch.object(voice_loop, "brain_reply",
                          side_effect=AssertionError("must not call")), \
             patch.object(voice_loop, "_store", return_value=FakeStore()):
            result = voice_loop.voice_turn(cancel_fn=lambda: True,
                                           status_fn=lambda *a: stages.append(a))
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "barge_in")
        self.assertEqual(stages[-1][0], "idle")
        self.assertEqual(stages[-1][2], "barge_in")

    def test_cancel_fn_after_brain_stops_speaking(self):
        import voice_loop

        heard = {"ok": True, "text": "salam", "language": "ar"}
        brain = {"ok": True, "text": "wa 3laykom", "model": "dolphin3"}
        with patch.object(voice_loop.local_voice, "listen", return_value=heard), \
             patch.object(voice_loop, "brain_reply", return_value=brain), \
             patch.object(voice_loop.local_voice, "speak",
                          side_effect=AssertionError("must not speak")), \
             patch.object(voice_loop, "_store", return_value=FakeStore()):
            result = voice_loop.voice_turn(cancel_fn=lambda: True)
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "barge_in")


    def test_action_request_waits_for_explicit_approval(self):
        import voice_loop

        heard = {"ok": True, "text": "lance un scan", "language": "fr"}
        brain = {"ok": True, "text": "je vais lancer le scan", "model": "dolphin3",
                 "action": {"action": "run", "target": "scan local", "reason": "demande vocale"}}

        class Store:
            def __init__(self):
                self.proposed = []

            def propose(self, action, target="", reason="", source="voice"):
                item = {"id": "act-1", "status": "proposed", "action": action,
                        "target": target, "reason": reason}
                self.proposed.append(item)
                return item

        store = Store()
        spoken = []
        with patch.object(voice_loop.local_voice, "listen", return_value=heard), \
             patch.object(voice_loop, "brain_reply", return_value=brain), \
             patch.object(voice_loop.local_voice, "speak",
                          side_effect=lambda text, **kw: spoken.append(text) or {"ok": True}), \
             patch.object(voice_loop, "_store", return_value=FakeStore()):
            result = voice_loop.voice_turn(action_store=store)
        self.assertTrue(result["ok"])
        self.assertTrue(result["approvalPending"])
        self.assertEqual(result["approval"]["status"], "proposed")
        self.assertEqual(len(store.proposed), 1)
        self.assertTrue(spoken)
        self.assertIn("approbation", spoken[0].lower())
        self.assertNotIn("je vais lancer le scan", spoken)


class DarijaNormalizeTest(unittest.TestCase):
    """J77 — la darija latine doit être comprise, pas renvoyée telle quelle."""

    def test_latin_darija_becomes_arabic_script(self):
        import voice_loop
        self.assertEqual(
            voice_loop.normalize_darija("salam, kifach ndir?"),
            "السلام عليكم، كي داير؟",
        )

    def test_arabic_script_is_untouched(self):
        import voice_loop
        text = "السلام عليكم، كي داير؟"
        self.assertEqual(voice_loop.normalize_darija(text), text)

    def test_unknown_english_is_untouched(self):
        import voice_loop
        text = "Hello, how are you?"
        self.assertEqual(voice_loop.normalize_darija(text), text)

    def test_common_words_are_translated(self):
        import voice_loop
        self.assertEqual(voice_loop.normalize_darija("wach bghiti?"), "واش بغيتي؟")


if __name__ == "__main__":
    unittest.main()
