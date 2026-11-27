"""J159 — TDD : voix locale d'Atulya pour le HUD, sans cloud ni secret."""

import io
import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock
from urllib.parse import quote

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import atulya_voice  # noqa: E402


def fake_wav():
    output = io.BytesIO()
    with wave.open(output, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(16000)
        writer.writeframes(b"\x00\x00" * 160)
    return output.getvalue()


class FakeEngine:
    def __init__(self, audio=None):
        self.ready = True
        self.calls = []
        self.audio = audio if audio is not None else fake_wav()

    def synthesize(self, text, language="auto"):
        self.calls.append((text, language))
        return self.audio


class AtulyaVoiceTest(unittest.TestCase):
    def test_synthese_retourne_un_wav_local(self):
        fake = FakeEngine()
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(atulya_voice, "CACHE_DIR", Path(tmp)), \
                mock.patch.object(atulya_voice, "engine", return_value=fake):
            audio = atulya_voice.synthesize("السلام عليكم، كيفاش الحال؟")
        self.assertTrue(audio.startswith(b"RIFF"))
        self.assertEqual(fake.calls, [("السلام عليكم، كيفاش الحال؟", "auto")])

    def test_texte_vide_et_trop_long_sont_refuses(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(atulya_voice, "CACHE_DIR", Path(tmp)):
            for text in ("", "   ", None, "x" * 501):
                with self.subTest(text=text), self.assertRaises(Exception):
                    atulya_voice.synthesize(text)

    def test_cache_evite_de_regenerer_le_meme_texte(self):
        fake = FakeEngine()
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(atulya_voice, "CACHE_DIR", Path(tmp)), \
                mock.patch.object(atulya_voice, "engine", return_value=fake):
            first = atulya_voice.synthesize("صباح الخير")
            second = atulya_voice.synthesize("صباح الخير")
        self.assertEqual(first, second)
        self.assertEqual(len(fake.calls), 1)

    def test_sortie_non_wav_est_refusee(self):
        fake = FakeEngine(audio=b"pas un wav")
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(atulya_voice, "CACHE_DIR", Path(tmp)), \
                mock.patch.object(atulya_voice, "engine", return_value=fake):
            with self.assertRaises(Exception):
                atulya_voice.synthesize("اختبار")

    def test_mesure_wav_sans_confondre_silence_et_son(self):
        silent = atulya_voice.wav_stats(fake_wav())
        self.assertEqual(silent["peak"], 0)
        self.assertFalse(silent["nonSilent"])
        output = io.BytesIO()
        with wave.open(output, "wb") as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(16000)
            writer.writeframes(b"\xff\x1f" * 1600)
        tone = atulya_voice.wav_stats(output.getvalue())
        self.assertTrue(tone["nonSilent"])
        self.assertGreater(tone["rms"], 10)

    def test_preuve_locale_reste_honnête_sur_l_écoute(self):
        fake = FakeEngine()
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(atulya_voice, "CACHE_DIR", Path(tmp)), \
                mock.patch.object(atulya_voice, "EVIDENCE_PATH", Path(tmp) / "evidence.json"), \
                mock.patch.object(atulya_voice, "engine", return_value=fake):
            proof = atulya_voice.write_evidence()
            saved = json.loads((Path(tmp) / "evidence.json").read_text(encoding="utf-8"))
        self.assertEqual(proof["status"], "implemented_unverified")
        self.assertEqual(proof["playback"], "owner_confirmation_pending")
        self.assertEqual(saved, proof)
        self.assertIn("127.0.0.1", proof["source"])

    def test_route_get_say_sans_corps_ni_post(self):
        text, language = atulya_voice.say_query(
            "/say?text=" + quote("أنا أتوليا، رديت عليك بالدارجة.") + "&language=auto"
        )
        self.assertEqual(text, "أنا أتوليا، رديت عليك بالدارجة.")
        self.assertEqual(language, "auto")
        self.assertEqual(atulya_voice.say_query("/say"), ("", "auto"))

    def test_health_est_honnête(self):
        with mock.patch.object(atulya_voice, "engine", return_value=FakeEngine()):
            self.assertEqual(atulya_voice.ready(), True)
        def broken():
            raise OSError("modele absent")
        with mock.patch.object(atulya_voice, "engine", side_effect=broken):
            self.assertEqual(atulya_voice.ready(), False)

    def test_aucun_reseau_externe_ni_executeur(self):
        source = (SRC / "atulya_voice.py").read_text(encoding="utf-8")
        for forbidden in ("subprocess", "requests", "httpx", "urllib.request", "touping",
                          "api_key", "elevenlabs", "openai"):
            self.assertNotIn(forbidden, source)
        self.assertIn('HOST = "127.0.0.1"', source)
        self.assertIn("PORT = 5105", source)


if __name__ == "__main__":
    unittest.main()
