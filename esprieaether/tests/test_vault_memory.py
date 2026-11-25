"""TDD : mémoire locale du vault Obsidian (BM25, hors ligne, sans dépendance)."""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

import vault_memory  # noqa: E402


class VaultMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self.tmp.name)
        (self.vault / "vision.md").write_text(
            "# Vision locale\nLe mmproj Qwen permet l'inférence visuelle avec llama.cpp.\n",
            encoding="utf-8")
        (self.vault / "voix.md").write_text(
            "# Voix\nBarge-in, micro et whisper pour couper la parole.\n", encoding="utf-8")
        (self.vault / "divers.md").write_text(
            "# Divers\nNotes sans rapport avec le modèle.\n", encoding="utf-8")
        hidden = self.vault / ".obsidian"
        hidden.mkdir()
        (hidden / "config.md").write_text("mmproj barge-in secret", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_bm25_returns_relevant_note_and_ignores_obsidian(self):
        memory = vault_memory.VaultMemory(self.vault)
        self.assertEqual(memory.count, 3)
        hits = memory.query("vision mmproj llama", limit=3)
        self.assertTrue(hits)
        self.assertEqual(hits[0]["path"], "vision.md")
        self.assertGreater(hits[0]["score"], 0)
        self.assertIn("mmproj", hits[0]["snippet"])
        self.assertFalse(any(".obsidian" in h["path"] for h in hits))

    def test_second_query_finds_voice_note(self):
        memory = vault_memory.VaultMemory(self.vault)
        hits = memory.query("barge-in micro", limit=3)
        self.assertEqual(hits[0]["path"], "voix.md")

    def test_empty_vault(self):
        empty = Path(self.tmp.name) / "empty"
        empty.mkdir()
        self.assertEqual(vault_memory.VaultMemory(empty).query("anything"), [])

    def test_evidence_writer_is_fresh_and_public(self):
        memory = vault_memory.VaultMemory(self.vault)
        evidence = memory.evidence("vision mmproj")
        self.assertTrue(evidence["ok"])
        self.assertIn("checkedAt", evidence)
        datetime.fromisoformat(evidence["checkedAt"])
        self.assertEqual(evidence["noteCount"], 3)
        self.assertEqual(evidence["topPath"], "vision.md")
        self.assertNotIn("secret", json.dumps(evidence, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
