"""J174 — réponses courtes véridiques + pont de fichiers local vers OpenCode."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.plugins import local_bridge


class LocalBridgeTest(unittest.TestCase):
    def test_qui_es_tu_repond_sans_modele_et_sans_inventer(self) -> None:
        intent = local_bridge.match_intent("من أنت؟")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.kind, "who")
        text = local_bridge.execute_intent(intent, Path(tempfile.mkdtemp()))
        self.assertIn("أتوليا", text)
        self.assertNotIn("live_verified", text)

    def test_esprieaether_est_un_alias_d_atulya(self) -> None:
        intent = local_bridge.match_intent("Esprieaether")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.kind, "who")
        text = local_bridge.execute_intent(intent, Path(tempfile.mkdtemp()))
        self.assertIn("أتوليا", text)
        self.assertIn("Esprieaether", text)

    def test_knowledge_avec_harf_latini_passe_par_le_local(self) -> None:
        intent = local_bridge.match_intent("CHENO LMA3RIFA LI 3ANDAK")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.kind, "knowledge")
        text = local_bridge.execute_intent(intent, Path(tempfile.mkdtemp()))
        self.assertIn("كاتالوج", text)
        self.assertNotIn("live_verified", text)

    def test_phrase_composee_avec_harf_latini_donne_un_apercu_honnete(self) -> None:
        phrase = "BERITAK TEDEWI OTEKOL LI CHENO KAYN F NIDAM ET CHEKOUN NETA ET CHENO KANTAWRO"
        intent = local_bridge.match_intent(phrase)
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.kind, "overview")
        folder = Path(tempfile.mkdtemp())
        (folder / "answers.jsonl").write_text(
            json.dumps({"kind": "answer", "text": "الخدمة شغّالة محلياً."}, ensure_ascii=False) + "\n",
            encoding="utf-8")
        text = local_bridge.execute_intent(intent, folder)
        self.assertIn("أتوليا", text)
        self.assertIn("الخدمة شغّالة محلياً.", text)
        self.assertNotIn("live_verified", text)

    def test_alias_opencode_en_harf_latini(self) -> None:
        asked = local_bridge.match_intent("وبن كود: واش كاين خدمة؟")
        self.assertIsNotNone(asked)
        assert asked is not None
        self.assertEqual(asked.kind, "ask")
        self.assertEqual(asked.target, "واش كاين خدمة")
        read = local_bridge.match_intent("CHENO KANTAWRO")
        self.assertIsNotNone(read)
        assert read is not None
        self.assertEqual(read.kind, "read")
        bare = local_bridge.match_intent("وبن كود")
        self.assertIsNotNone(bare)
        assert bare is not None
        self.assertEqual(bare.kind, "hint")
        self.assertIn("سول أوبن كود", local_bridge.execute_intent(bare, Path(tempfile.mkdtemp())))

    def test_capacites_sont_decrites_sans_etat_vivant_invente(self) -> None:
        intent = local_bridge.match_intent("شنو تقدر تدير؟")
        self.assertIsNotNone(intent)
        assert intent is not None
        text = local_bridge.execute_intent(intent, Path(tempfile.mkdtemp()))
        self.assertIn("يوتيوب", text)
        self.assertNotIn("executed", text)

    def test_demande_de_status_ne_passe_pas_par_le_pont(self) -> None:
        self.assertIsNone(local_bridge.match_intent("حالة الأنظمة"))
        self.assertIsNone(local_bridge.match_intent("تقرير سريع عن كل الأنظمة"))

    def test_question_ecrite_dans_le_dossier_partage_sans_secret(self) -> None:
        intent = local_bridge.match_intent("سول أوبن كود: api_key=secret456 واش كاين خدمة؟")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.kind, "ask")
        with tempfile.TemporaryDirectory() as tmp:
            text = local_bridge.execute_intent(intent, Path(tmp))
            rows = [json.loads(line) for line in (Path(tmp) / "questions.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertTrue(rows[0]["id"].startswith("q-"))
            self.assertEqual(rows[0]["status"], "pending")
            self.assertIn("واش كاين خدمة", rows[0]["text"])
            self.assertNotIn("secret456", (Path(tmp) / "questions.jsonl").read_text(encoding="utf-8"))
            self.assertIn("سجّلت", text)
            self.assertNotIn("جاوب", text.split(".")[0])

    def test_lecture_sans_reponse_est_honnete(self) -> None:
        intent = local_bridge.match_intent("شنو قال أوبن كود؟")
        self.assertIsNotNone(intent)
        assert intent is not None
        text = local_bridge.execute_intent(intent, Path(tempfile.mkdtemp()))
        self.assertIn("ما جاتنيش", text)
        self.assertNotIn("قال:", text)

    def test_lecture_rend_le_texte_du_fichier_uniquement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "answers.jsonl").write_text(
                json.dumps({"kind": "answer", "question_id": "q-123", "text": "الخدمة شغّالة."}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            intent = local_bridge.match_intent("رد أوبن كود")
            self.assertIsNotNone(intent)
            text = local_bridge.execute_intent(intent, folder)
            self.assertEqual(text.strip(), "الخدمة شغّالة.")

    def test_reponse_vide_ignoree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "answers.jsonl").write_text(
                json.dumps({"kind": "answer", "text": "   "}, ensure_ascii=False) + "\n", encoding="utf-8")
            intent = local_bridge.match_intent("شنو جاوب أوبن كود؟")
            self.assertIsNotNone(intent)
            self.assertIn("ما جاتنيش", local_bridge.execute_intent(intent, folder))

    def test_question_ordinaire_ne_devient_pas_un_pont(self) -> None:
        self.assertIsNone(local_bridge.match_intent("كيفاش كيخدم الصوت؟"))
        self.assertIsNone(local_bridge.match_intent("شغّل موسيقى راب مغربي"))


if __name__ == "__main__":
    unittest.main()
