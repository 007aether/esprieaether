"""J184 — معرفة openset-llm محلية، صادقة، بلا شبكة وبلا حالة حية مفترضة."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.plugins import openset_llm

META = Path(__file__).resolve().parents[2] / "tools" / "plugins" / "openset_llm.json"


class OpenSetLlmTest(unittest.TestCase):
    def test_metadata_contient_repo_et_pas_de_secret(self) -> None:
        data = json.loads(META.read_text(encoding="utf-8"))
        self.assertEqual(data["repo"], "opensetlabs/openset-llm")
        self.assertEqual(data["license"], "MIT")
        self.assertFalse(data["installed"])
        self.assertFalse(data["endpointProposal"]["enabled"])
        raw = META.read_text(encoding="utf-8").lower()
        self.assertNotIn("hf_token=", raw)
        self.assertNotIn("api_key=", raw)

    def test_what_donne_description_sans_dire_que_chaque(self) -> None:
        intent = openset_llm.match_intent("شنو هو openset-llm")
        self.assertIsNotNone(intent)
        assert intent is not None
        text = openset_llm.execute_intent(intent)
        self.assertIn("opensetlabs/openset-llm", text)
        self.assertIn("MIT", text)
        self.assertIn("ما كيأكدش", text)
        self.assertNotIn("live_verified", text)

    def test_how_donne_endpoint_sans_activer_le_proviseur(self) -> None:
        intent = openset_llm.match_intent("كيفاش نستعمل openset-llm")
        self.assertIsNotNone(intent)
        assert intent is not None
        text = openset_llm.execute_intent(intent)
        self.assertIn("http://127.0.0.1:8080/v1", text)
        self.assertIn("WSL2", text)
        self.assertIn("ما نزّلتش الموديل", text)

    def test_status_donne_progression_reelle_sans_dire_live(self) -> None:
        intent = openset_llm.match_intent("شنو حالة openset-llm")
        self.assertIsNotNone(intent)
        assert intent is not None
        text = openset_llm.execute_intent(intent)
        self.assertIn("Ubuntu2404", text)
        self.assertIn("كيتحمّل", text)
        self.assertIn("ما تحققش حياً", text)
        self.assertNotIn("live_verified", text)

    def test_status_latin_darija(self) -> None:
        intent = openset_llm.match_intent("kifach kayn l 7al openset llm")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.kind, "status")

    def test_status_darija_naturelle_sans_nom_moteur(self) -> None:
        for phrase in ("واش تحمّل الموديل", "فين وصل التحميل", "كمّل التحميل"):
            with self.subTest(phrase=phrase):
                intent = openset_llm.match_intent(phrase)
                self.assertIsNotNone(intent)
                assert intent is not None
                self.assertEqual(intent.kind, "status")

    def test_question_ordinaire_ne_devient_pas_openset(self) -> None:
        self.assertIsNone(openset_llm.match_intent("حالة الأنظمة"))
        self.assertIsNone(openset_llm.match_intent("عطيني المشاريع"))


if __name__ == "__main__":
    unittest.main()
