"""J93 — dépôt de vraies sources documentaires, avec empreinte et sans invention."""

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

from sources_intake import ingest  # noqa: E402


class SourcesIntakeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "sources"
        self.provenance = Path(self.tmp.name) / "state" / "sources_intake.jsonl"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_unknown_category_is_refused(self) -> None:
        src = Path(self.tmp.name) / "loi.txt"
        src.write_text("Loi réelle déposée par l'utilisateur", encoding="utf-8")
        with self.assertRaises(ValueError):
            ingest(src, "finance", root=self.root, provenance_path=self.provenance)

    def test_templates_empty_and_missing_files_are_refused(self) -> None:
        for name, content in (("_modele.md", "à remplir"), ("README.md", "doc"), (".gitkeep", "")):
            with self.subTest(name=name):
                src = Path(self.tmp.name) / name
                src.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    ingest(src, "legal", root=self.root, provenance_path=self.provenance)
        with self.assertRaises(ValueError):
            ingest(Path(self.tmp.name) / "absent.txt", "legal",
                   root=self.root, provenance_path=self.provenance)

    def test_real_file_is_copied_with_hash_and_provenance(self) -> None:
        payload = "Bail signé le 12/01/2026 — pièce réelle fournie par l'utilisateur.\n"
        src = Path(self.tmp.name) / "bail signé.txt"
        src.write_text(payload, encoding="utf-8")
        expected = src.read_bytes()
        result = ingest(src, "legal", root=self.root, provenance_path=self.provenance)
        self.assertEqual(result["category"], "legal")
        self.assertEqual(result["bytes"], len(expected))
        self.assertEqual(result["sha256"], hashlib.sha256(expected).hexdigest())
        copied = self.root / "legal" / "bail_signé.txt"
        self.assertTrue(copied.is_file())
        self.assertEqual(copied.read_bytes(), expected)
        lines = self.provenance.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        self.assertIn(result["sha256"], lines[0])

    def test_conflicting_destination_is_refused_without_overwrite(self) -> None:
        src = Path(self.tmp.name) / "bareme.txt"
        src.write_text("Barème vérifié fourni par l'utilisateur", encoding="utf-8")
        ingest(src, "fiscal", root=self.root, provenance_path=self.provenance)
        src.write_text("Contenu different et non verifie", encoding="utf-8")
        with self.assertRaises(ValueError):
            ingest(src, "fiscal", root=self.root, provenance_path=self.provenance)
        self.assertIn("Barème vérifié",
                      (self.root / "fiscal" / "bareme.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
