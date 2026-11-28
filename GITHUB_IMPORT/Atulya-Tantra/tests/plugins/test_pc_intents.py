"""J171 — TDD des intentions PC/Internet en darja, sans résultat inventé."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.plugins import pc_intents
from pc_gateway import PcGateway


class FakeGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def request(self, kind: str, target: str, *, mode: str = "ask_each") -> dict:
        self.calls.append((kind, target, mode))
        return {"text": "تم الطلب: " + target[:30], "status": "proposed", "id": "act-test"}


class PcIntentTest(unittest.TestCase):
    def test_musique_rap_maroc_ouvre_youtube_en_attendant_approbation(self) -> None:
        intent = pc_intents.match_intent("شغّل موسيقى راب مغربي")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.kind, "open_url")
        self.assertIn("youtube.com/results", intent.target)
        self.assertIn("search_query=rap+maroc", intent.target)
        self.assertEqual(intent.mode, "ask_each")

    def test_youtube_seul_ouvre_la_page_d_accueil(self) -> None:
        intent = pc_intents.match_intent("افتح يوتيوب")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.target, pc_intents.YOUTUBE_HOME)

    def test_commande_ecrite_passe_par_la_passerelle_sans_execution_directe(self) -> None:
        intent = pc_intents.match_intent("دير هادي: echo مرحبا")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.kind, "run_command")
        self.assertEqual(intent.target, "echo مرحبا")
        gateway = FakeGateway()
        result = pc_intents.execute_intent(intent, gateway)
        self.assertEqual(gateway.calls, [("run_command", "echo مرحبا", "ask_each")])
        self.assertEqual(result["status"], "proposed")
        self.assertNotIn("نفّذت", result["text"])

    def test_mode_auto_demande_par_la_phrase_bila_soual(self) -> None:
        intent = pc_intents.match_intent("دير هادي: بلا سؤال echo hello")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.mode, "auto")
        self.assertEqual(intent.target, "echo hello")

    def test_ligne_rouge_refusee_avant_toute_execution(self) -> None:
        intent = pc_intents.match_intent("دير هادي: بلا سؤال type .env")
        self.assertIsNotNone(intent)
        with tempfile.TemporaryDirectory() as tmp:
            gateway = PcGateway(state_dir=Path(tmp),
                                browser_open=lambda url: None,
                                runner=lambda command, timeout: {"ok": True, "stdout": "SECRET"})
            result = pc_intents.execute_intent(intent, gateway)
            self.assertEqual(result["status"], "refused")
            self.assertNotIn("SECRET", result["text"])

    def test_confirmation_par_texte_utilise_la_passerelle(self) -> None:
        intent = pc_intents.match_intent("أكدت act-d41a4ce941")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.kind, "decide")
        self.assertEqual(intent.target, "act-d41a4ce941")
        self.assertEqual(intent.mode, "approved_once")

    def test_Confirm_مختصر_مقيد_بطلب_واحد_معلق(self) -> None:
        intent = pc_intents.match_intent("أكدت")
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.kind, "decide_last")
        self.assertEqual(intent.target, "approved_once")
        with tempfile.TemporaryDirectory() as tmp:
            gateway = PcGateway(state_dir=Path(tmp), browser_open=lambda url: None)
            self.assertEqual(gateway.request("open_url", pc_intents.YOUTUBE_HOME)["status"], "proposed")
            result = pc_intents.execute_intent(intent, gateway)
            self.assertEqual(result["status"], "executed")
            self.assertEqual(gateway.last_result()["executed"], True)

    def test_Confirm_مختصر_يرفض_عند_تعدد_الطلبات(self) -> None:
        intent = pc_intents.match_intent("أكدت")
        assert intent is not None
        with tempfile.TemporaryDirectory() as tmp:
            gateway = PcGateway(state_dir=Path(tmp), browser_open=lambda url: None)
            gateway.request("open_url", pc_intents.YOUTUBE_HOME)
            gateway.request("open_url", "https://www.youtube.com/results?search_query=rap+maroc")
            result = pc_intents.execute_intent(intent, gateway)
            self.assertEqual(result["status"], "refused")
            self.assertEqual(len(gateway.browser_calls), 0)
            self.assertIn("أكدت act-", result["text"])

    def test_Confirm_مختصر_ما ينفذش_بلا_طلب(self) -> None:
        intent = pc_intents.match_intent("أكدت")
        assert intent is not None
        with tempfile.TemporaryDirectory() as tmp:
            gateway = PcGateway(state_dir=Path(tmp), browser_open=lambda url: None)
            result = pc_intents.execute_intent(intent, gateway)
            self.assertEqual(result["status"], "refused")
            self.assertEqual(gateway.browser_calls, [])

    def test_url_private_refusee(self) -> None:
        self.assertIsNone(pc_intents.match_intent("افتح http://127.0.0.1:8501/"))

    def test_question_ordinaire_ne_devient_pas_une_action(self) -> None:
        self.assertIsNone(pc_intents.match_intent("كيفاش كيخدم الصوت؟"))


if __name__ == "__main__":
    unittest.main()
