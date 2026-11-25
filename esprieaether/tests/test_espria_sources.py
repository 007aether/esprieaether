"""Les agents A4/L1/L2 lisent de vrais documents locaux, ou disent explicitement qu'ils n'en ont pas."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

# Même isolement que test_espria_system : état temporaire persistant pendant
# tout le processus, sinon la base réelle contient déjà un utilisateur "kamal".
_STATE_TMP = tempfile.TemporaryDirectory()
os.environ["ESPRIA_STATE_DIR"] = _STATE_TMP.name
os.environ["WEB_SECRET_KEY"] = "test-secret-not-a-real-key"
os.environ["FREELLMAPI_KEY"] = "test-key-placeholder"

import espria_system  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


class AgentSourcesTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        for name in ("legal", "fiscal", "travail"):
            (self.root / name).mkdir()
        self._patch = patch.object(espria_system, "AGENT_SOURCE_DIRS", {
            "A4": self.root / "legal",
            "L1": self.root / "fiscal",
            "L2": self.root / "travail",
        })
        self._patch.start()
        self.client = TestClient(espria_system.app)

    def tearDown(self):
        self._patch.stop()
        self._tmp.cleanup()

    def test_no_document_returns_explicit_no_data_source(self):
        for agent in ("A4", "L1", "L2"):
            response = self.client.get(f"/agents/{agent}/run")
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body["status"], "no_data_source")
            self.assertIn(str(self.root), body["source"])
            self.assertEqual(body["summary"], {})

    def test_real_document_is_read_verbatim_and_templates_ignored(self):
        (self.root / "fiscal" / "bareme.txt").write_text("TVA 20% — barème vérifié", encoding="utf-8")
        (self.root / "fiscal" / "_modele.md").write_text("à remplir", encoding="utf-8")
        response = self.client.get("/agents/L1/run")
        body = response.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["summary"]["documents"], 1)
        excerpt = body["summary"]["excerpts"][0]
        self.assertEqual(excerpt["file"], "bareme.txt")
        self.assertIn("TVA 20%", excerpt["text"])
        self.assertNotIn("à remplir", str(body))


if __name__ == "__main__":
    unittest.main()
