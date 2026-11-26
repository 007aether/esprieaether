"""J121 — TDD : compatibilité des appelants existants de rea_agent."""

import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import rea_agent  # noqa: E402


class ReaCompatTest(unittest.TestCase):
    def test_doctor_est_une_lecture_locale_sans_cli_externe(self) -> None:
        result = rea_agent.doctor()
        self.assertIsInstance(result, dict)
        self.assertIn("ok", result)
        self.assertIn("skill", result)
        self.assertTrue(result["ok"])

    def test_analyze_investigate_et_inventory_acceptent_un_dossier_local(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sample.py").write_text("def main():\n    pass\n", encoding="utf-8")
            analysis = rea_agent.analyze(root)
            self.assertTrue(analysis["ok"])
            self.assertEqual(analysis["files"], 1)
            investigated = rea_agent.investigate(root)
            self.assertTrue(investigated["ok"])
            self.assertIn("result", investigated)
            inventory = rea_agent.inventory(root)
            self.assertTrue(inventory["ok"])

    def test_status_report_est_en_arabe_sans_reseau(self) -> None:
        text = rea_agent.status_report()
        self.assertTrue(any("\u0600" <= ch <= "\u06ff" for ch in text))
        self.assertIn("REA", text)

    def test_aucune_commande_externe_dans_le_module(self) -> None:
        source = (SRC / "rea_agent.py").read_text(encoding="utf-8")
        self.assertNotIn("import subprocess", source)
        self.assertNotIn("import urllib", source)
        self.assertNotIn("pkill", source)


if __name__ == "__main__":
    unittest.main()
