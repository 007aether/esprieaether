"""J182 — catalogue GitHub local: 50 projets, sans réseau et sans état inventé."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.plugins import github_catalog

CATALOG = Path(__file__).resolve().parents[2] / "tools" / "plugins" / "github_catalog.json"


class GithubCatalogTest(unittest.TestCase):
    def test_catalogue_contient_50_projets_uniques_sans_secret(self) -> None:
        data = json.loads(CATALOG.read_text(encoding="utf-8"))
        projects = data["projects"]
        self.assertEqual(len(projects), 50)
        self.assertEqual(len({p["full_name"] for p in projects}), 50)
        self.assertTrue(data["collectedAt"])
        raw = CATALOG.read_text(encoding="utf-8").lower()
        self.assertNotIn("api_key=", raw)
        self.assertNotIn("authorization=", raw)

    def test_liste_donne_les_50_sans_status(self) -> None:
        intent = github_catalog.match_intent("عطيني المشاريع")
        self.assertIsNotNone(intent)
        assert intent is not None
        text = github_catalog.execute_intent(intent, CATALOG)
        self.assertIn("50 المشاريع", text)
        self.assertIn("morluto/rea", text)
        self.assertNotIn("live_verified", text)
        self.assertNotIn("executed", text)

    def test_detail_par_rang(self) -> None:
        intent = github_catalog.match_intent("تفاصيل المشروع 1")
        assert intent is not None
        text = github_catalog.execute_intent(intent, CATALOG)
        self.assertIn("morluto/rea", text)
        self.assertIn("الرابط: https://github.com/morluto/rea", text)
        self.assertIn("★", text)
        self.assertIn(" forks ", text)
        self.assertIn("باقي شغّال", text)

    def test_detail_par_nom_court_et_complet(self) -> None:
        for question in ("تفاصيل rea", "شنو المشروع deepseek-ai/deepseek-harness"):
            intent = github_catalog.match_intent(question)
            self.assertIsNotNone(intent, question)
            assert intent is not None
            text = github_catalog.execute_intent(intent, CATALOG)
            self.assertIn("الوصف:", text)

    def test_recherche_par_mot_cle(self) -> None:
        intent = github_catalog.match_intent("مشاريع على voice")
        assert intent is not None
        text = github_catalog.execute_intent(intent, CATALOG)
        self.assertIn("لقيت", text)
        self.assertIn("VoiceStudio", text)

    def test_recherche_sans_resultat_est_honnete(self) -> None:
        intent = github_catalog.match_intent("مشاريع على quantum-xyz-123")
        assert intent is not None
        text = github_catalog.execute_intent(intent, CATALOG)
        self.assertIn("ما لقيتش", text)
        self.assertNotIn("★", text)

    def test_projet_inconnu_est_honnete(self) -> None:
        intent = github_catalog.match_intent("تفاصيل projet-inexistant-999")
        assert intent is not None
        self.assertIn("ما لقيتش", github_catalog.execute_intent(intent, CATALOG))

    def test_projet_unifie_dedie_a_esprieaether(self) -> None:
        for question in ("شنو المشروع اللي كيجمع كلشي", "chi projet ijema33 kolechi widifo l esprieaether"):
            intent = github_catalog.match_intent(question)
            self.assertIsNotNone(intent, question)
            assert intent is not None
            self.assertEqual(intent.kind, "unified")
            text = github_catalog.execute_intent(intent, CATALOG)
            self.assertIn("affaan-m/ECC", text)
            self.assertIn("Esprieaether", text)
            self.assertIn("ما كتعنيش", text)

    def test_questions_ordinaires_ne_deviennent_pas_un_catalogue(self) -> None:
        self.assertIsNone(github_catalog.match_intent("حالة الأنظمة"))
        self.assertIsNone(github_catalog.match_intent("كيفاش كيخدم الصوت؟"))
        self.assertIsNone(github_catalog.match_intent("شغّل موسيقى راب مغربي"))

    def test_fichier_manquant_est_honnete(self) -> None:
        intent = github_catalog.match_intent("عطيني المشاريع")
        assert intent is not None
        text = github_catalog.execute_intent(intent, Path("introuvable.json"))
        self.assertIn("غير متوفر", text)
        self.assertNotIn("50", text)


if __name__ == "__main__":
    unittest.main()
