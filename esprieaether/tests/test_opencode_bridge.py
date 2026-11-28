"""J174 — le pont de fichiers entre Atulya et OpenCode reste local et véridique."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "opencode_bridge.py"
_spec = importlib.util.spec_from_file_location("opencode_bridge_cli", _SCRIPT)
bridge = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(bridge)


class OpenCodeBridgeTest(unittest.TestCase):
    def test_question_sans_reponse_reste_en_attente(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "questions.jsonl").write_text(
                json.dumps({"kind": "question", "id": "q-abc12345", "text": "شنو؟"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            rows = bridge.pending(folder)
            self.assertEqual([row["id"] for row in rows], ["q-abc12345"])

    def test_reponse_ecrite_retire_la_question_de_la_liste(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "questions.jsonl").write_text(
                json.dumps({"kind": "question", "id": "q-abc12345", "text": "شنو؟"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            row = bridge.answer("q-abc12345", "الجواب من OpenCode.", folder)
            self.assertEqual(row["answeredBy"], "opencode")
            self.assertEqual(bridge.pending(folder), [])
            self.assertIn("الجواب", (folder / "answers.jsonl").read_text(encoding="utf-8"))

    def test_reponse_vide_ou_identifiant_faux_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                bridge.answer("not-an-id", "جواب", Path(tmp))
            with self.assertRaises(ValueError):
                bridge.answer("q-abc12345", "   ", Path(tmp))
            self.assertFalse((Path(tmp) / "answers.jsonl").exists())

    def test_aucun_secret_dans_la_reponse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            row = bridge.answer("q-abc12345", "api_key=secret999 استعملتها", Path(tmp))
            self.assertNotIn("secret999", row["text"])
            self.assertNotIn("secret999", (Path(tmp) / "answers.jsonl").read_text(encoding="utf-8"))

    def test_cli_pending_et_answer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "questions.jsonl").write_text(
                json.dumps({"kind": "question", "id": "q-cli1234", "text": "سؤال"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(bridge.main(["--dir", str(folder), "pending"]), 0)
            self.assertEqual(bridge.main(["--dir", str(folder), "answer", "q-cli1234", "جاوبت"]), 0)
            self.assertEqual(bridge.pending(folder), [])


if __name__ == "__main__":
    unittest.main()
