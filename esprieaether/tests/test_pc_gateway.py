"""J171 — TDD de la passerelle d'actions PC/Internet gouvernée.

Le propriétaire a autorisé : Internet complet, exécution des commandes qu'il
écrit, et les trois modes de consentement. Les lignes rouges permanentes
(touping.exe, .env/clés, SMS/call/appareil) restent refusées même en mode auto.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pc_gateway


class PcGatewayTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.gateway = pc_gateway.PcGateway(
            state_dir=root,
            browser_open=lambda url: "opened:" + url,
            runner=lambda command, timeout: {
                "ok": True, "stdout": "hello\n", "stderr": "", "code": 0,
            },
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_public_youtube_url_avec_query_est_acceptee(self) -> None:
        url = "https://www.youtube.com/results?search_query=rap+maroc"
        self.assertTrue(pc_gateway.is_public_web_url(url))

    def test_loopback_et_scheme_hors_http_sont_refuses(self) -> None:
        for url in (
            "http://127.0.0.1:8501/", "http://localhost/", "file:///C:/x",
            "https://user:pass@example.com/", "https://192.168.1.4/",
        ):
            with self.subTest(url=url):
                self.assertFalse(pc_gateway.is_public_web_url(url))

    def test_lignes_rouges_sont_refusees_meme_en_auto(self) -> None:
        refused = (
            "touping.exe",
            "type .env",
            "cat .env",
            "adb shell am start -a android.intent.action.CALL",
            "send sms",
            "rm -rf C:\\Users",
        )
        for command in refused:
            with self.subTest(command=command):
                decision = self.gateway.request("run_command", command, mode="auto")
                self.assertEqual(decision["status"], "refused")
                self.assertIn("red_line", decision["reason"])

    def test_open_url_ask_each_reste_en_attente(self) -> None:
        plan = self.gateway.request(
            "open_url", "https://www.youtube.com/results?search_query=rap+maroc")
        self.assertEqual(plan["status"], "proposed")
        self.assertFalse(self.gateway.last_result()["executed"])
        self.assertEqual(self.gateway.browser_calls, [])

    def test_open_url_approved_once_s_execute_et_est_audité(self) -> None:
        plan = self.gateway.request(
            "open_url", "https://www.youtube.com/results?search_query=rap+maroc")
        done = self.gateway.decide(plan["id"], "approved_once")
        self.assertEqual(done["status"], "executed")
        self.assertEqual(self.gateway.browser_calls,
                         ["https://www.youtube.com/results?search_query=rap+maroc"])
        last = self.gateway.last_result()
        self.assertTrue(last["executed"])
        self.assertIn("youtube", last["text"])
        audit = (Path(self.tmp.name) / "pc_action_audit.jsonl").read_text(encoding="utf-8")
        self.assertIn("proposed", audit)
        self.assertIn("approved_once", audit)
        self.assertIn("executed", audit)

    def test_mode_auto_execute_directement_sans_demande(self) -> None:
        plan = self.gateway.request("run_command", "echo hello", mode="auto")
        self.assertEqual(plan["status"], "executed")
        self.assertIn("hello", plan["text"])
        self.assertEqual(self.gateway.runner_calls, [("echo hello", 20)])

    def test_mode_session_reutilise_le_grant_pour_la_meme_cible(self) -> None:
        first = self.gateway.request("run_command", "echo hello", mode="session")
        self.assertEqual(first["status"], "proposed")
        self.gateway.decide(first["id"], "approved_once")
        second = self.gateway.request("run_command", "echo hello", mode="session")
        self.assertEqual(second["status"], "executed")
        self.assertEqual(len(self.gateway.runner_calls), 2)
        other = self.gateway.request("run_command", "echo autre", mode="session")
        self.assertEqual(other["status"], "proposed")

    def test_refus_explicite_ne_execute_rien(self) -> None:
        plan = self.gateway.request("open_url", "https://example.com/")
        denied = self.gateway.decide(plan["id"], "denied")
        self.assertEqual(denied["status"], "denied")
        self.assertEqual(self.gateway.browser_calls, [])

    def test_resultat_est_ecrit_en_json_local_sans_secret(self) -> None:
        self.gateway.request("run_command", "echo api_key=secret123", mode="auto")
        raw = (Path(self.tmp.name) / "pc_action_last.json").read_text(encoding="utf-8")
        self.assertNotIn("secret123", raw)
        self.assertIn("[redacted]", raw)


if __name__ == "__main__":
    unittest.main()
