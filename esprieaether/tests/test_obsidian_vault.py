"""Gate tests for the Obsidian vault builder and knowledge-graph renderer.

Uses a temporary vault and a temporary "real project" so tests never touch the
user's live ~/ObsidianVault/EsprieAether.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

BASE_DIR = Path(__file__).resolve().parents[1]
_TMP = tempfile.TemporaryDirectory()
_ROOT = Path(_TMP.name)
_FAKE_PROJECT = _ROOT / "project"
(_FAKE_PROJECT / "docs").mkdir(parents=True)
(_FAKE_PROJECT / "docs" / "SOP_WIKI.md").write_text(
    "# SOP réel\n\nProcédure vérifiée.\n", encoding="utf-8"
)
(_FAKE_PROJECT / "docs" / "GAP_ANALYSIS.md").write_text(
    "# GAP réel\n\nÉcart vérifié.\n", encoding="utf-8"
)
_FAKE_SUNNAVOK = _ROOT / "sunnavok"
(_FAKE_SUNNAVOK / "07_Obsidian_Legacy" / "Sunna-Equipe-Industrial").mkdir(parents=True)
(_FAKE_SUNNAVOK / "01_Company").mkdir(parents=True)
(_FAKE_SUNNAVOK / "07_Obsidian_Legacy" / "Sunna-Equipe-Industrial" / "Bots.md").write_text(
    "# Bots historiques\n\nVeille, Al_Afdal, Souk, Offres, Pinterest.\n", encoding="utf-8"
)
(_FAKE_SUNNAVOK / "00_HOME_SUNNAVOK.md").write_text(
    "# Accueil historique\n\nLien vers les archives.\n", encoding="utf-8"
)
(_FAKE_SUNNAVOK / "01_Company" / "Company_Hub.md").write_text(
    "# Company Hub\n\nSARL AU.\n", encoding="utf-8"
)
os.environ["ESPRIE_DIR"] = str(_FAKE_PROJECT)
os.environ["SUNNAVOK_DIR"] = str(_FAKE_SUNNAVOK)
os.environ["OBSIDIAN_VAULT_DIR"] = str(_ROOT / "vault")

sys.path.insert(0, str(BASE_DIR / "src"))
import obsidian_graph_web as graph  # noqa: E402
import obsidian_vault_builder as builder  # noqa: E402


class ObsidianVaultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        builder.main()
        graph.main()

    @classmethod
    def tearDownClass(cls):
        _TMP.cleanup()

    def _note(self, rel):
        path = builder.VAULT / rel
        self.assertTrue(path.exists(), f"note absente: {rel}")
        return path.read_text(encoding="utf-8")

    def test_builder_console_output_survives_windows_cp1252(self):
        """Le daemon lance les tests sans PYTHONIOENCODING : aucun emoji dans print()."""
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "cp1252"
        env["ESPRIE_DIR"] = str(_FAKE_PROJECT)
        env["SUNNAVOK_DIR"] = str(_FAKE_SUNNAVOK)
        env["OBSIDIAN_VAULT_DIR"] = str(_ROOT / "vault-console")
        for script, marker in (
            ("obsidian_vault_builder.py", "Obsidian vault:"),
            ("obsidian_graph_web.py", "graph.html:"),
        ):
            with self.subTest(script=script):
                proc = subprocess.run(
                    [sys.executable, str(BASE_DIR / "src" / script)],
                    cwd=str(BASE_DIR), env=env, capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=60,
                )
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertIn(marker, proc.stdout)
                self.assertNotIn("UnicodeEncodeError", proc.stderr)

    def test_docs_come_from_real_project_not_desktop(self):
        for rel in ("Docs/SOP_WIKI.md", "Docs/GAP_ANALYSIS.md"):
            text = self._note(rel)
            self.assertNotIn("_not found_", text, rel)
            self.assertIn("vérifié", text, rel)

    def test_services_reflect_verified_reality(self):
        cloud = self._note("Services/cloud-desktop.md")
        self.assertIn("5001", cloud)
        self.assertIn("EspriaAether", cloud)
        self.assertIn("5000", self._note("Services/web.md"))
        llm = self._note("Services/freellmapi.md")
        self.assertIn("31415", llm)
        self.assertIn("Arrêté", self._note("Services/ollama.md"))

    def test_obsidian_agents_are_registered(self):
        for agent in ("A1", "A2", "A3", "A4", "M1", "L1", "L2", "director"):
            text = self._note(f"Agents/{agent}.md")
            self.assertIn("/agents/", text, agent)
        self.assertIn("no_data_source", self._note("Agents/A4.md"))

    def test_verified_status_note_exists(self):
        text = self._note("Meta/ETAT_VERIFIE.md")
        self.assertIn("Confirmé", text)
        self.assertIn("non vérifiées", text)
        self.assertIn("no_data_source", text)
        self.assertIn("401", text)

    def test_all_old_notes_are_imported_without_deletion(self):
        legacy = self._note("Legacy/Bots.md")
        self.assertIn("Al_Afdal", legacy)
        self.assertIn("## Liens", legacy)
        self.assertIn("Accueil historique", self._note("SUNNAVOK/ROOT__00_HOME_SUNNAVOK.md"))
        self.assertIn("SARL AU", self._note("SUNNAVOK/01_Company__Company_Hub.md"))
        status = self._note("Meta/ETAT_VERIFIE.md")
        self.assertIn("Archives importées", status)
        self.assertIn("Sources encore manquantes", status)
        self.assertIn("data/sources", status)

    def test_graph_is_offline_and_nonempty(self):
        html = (builder.VAULT / "graph.html").read_text(encoding="utf-8")
        self.assertNotIn("unpkg.com", html)
        self.assertIn("new vis.Network", html)
        # La bibliothèque est inline : le HTML doit être nettement plus gros
        # que la version CDN (~26 Ko) et inclure l'en-tête du fichier vendored.
        self.assertGreater(len(html), 600000)
        vendor_head = graph.VENDOR_JS.read_text(encoding="utf-8", errors="ignore")[:2000]
        self.assertIn(vendor_head, html)
        nodes, edges = graph.parse_vault()
        self.assertGreater(len(nodes), 100)
        self.assertGreater(len(edges), 200)

    def test_graph_keeps_duplicate_notes_distinct_and_drops_broken_links(self):
        with tempfile.TemporaryDirectory(prefix="obsidian-graph-") as tmp:
            vault = Path(tmp)
            (vault / "Services").mkdir()
            (vault / "Sunna").mkdir()
            (vault / "Services" / "email.md").write_text(
                "# email\n\n[[_Index]] [[missing-note]] [[Sunna]]\n", encoding="utf-8")
            (vault / "Sunna" / "email.md").write_text(
                "# email\n\n[[Sunna]]\n", encoding="utf-8")
            (vault / "Sunna" / "Sunna.md").write_text(
                "# Sunna\n\n[[email]]\n", encoding="utf-8")
            (vault / "_Index.md").write_text("# Index\n\n[[email]]\n", encoding="utf-8")
            with mock.patch.object(graph, "VAULT", vault):
                nodes, edges = graph.parse_vault()
            ids = [item["id"] for item in nodes]
            self.assertEqual(len(ids), len(set(ids)), ids)
            self.assertIn("Services/email", ids)
            self.assertIn("Sunna/email", ids)
            self.assertIn("_Index", ids)
            targets = {item["to"] for item in edges}
            self.assertNotIn("missing-note", targets)
            self.assertNotIn("email", targets)
            self.assertEqual(len(edges), len({(e["from"], e["to"]) for e in edges}))
            self.assertTrue(all(e["from"] != e["to"] for e in edges))

    def test_repair_rewrites_ambiguous_links_and_removes_dead_ones(self):
        with tempfile.TemporaryDirectory(prefix="obsidian-repair-") as tmp:
            vault = Path(tmp)
            (vault / "Services").mkdir()
            (vault / "Sunna").mkdir()
            (vault / "Services" / "email.md").write_text("# e\n\n[[Sunna]]\n", encoding="utf-8")
            (vault / "Sunna" / "email.md").write_text("# e\n\n[[Sunna]]\n", encoding="utf-8")
            (vault / "Sunna" / "Sunna.md").write_text(
                "# Sunna\n\n[[email]] avant [[dead-link]] après\n", encoding="utf-8")
            with mock.patch.object(graph, "VAULT", vault):
                stats = graph.repair_wiki_links()
                nodes, edges = graph.parse_vault()
            text = (vault / "Sunna" / "Sunna.md").read_text(encoding="utf-8")
            self.assertIn("[[Sunna/email]]", text)
            self.assertNotIn("dead-link", text)
            self.assertEqual(stats["removed"], 1)
            self.assertEqual(stats["notes"], stats["notes_after"])
            self.assertTrue(all(e["to"] in {n["id"] for n in nodes} for e in edges))

    def test_deduplicate_reNames_copies_and_keeps_links_resolvable(self):
        with tempfile.TemporaryDirectory(prefix="obsidian-dedupe-") as tmp:
            vault = Path(tmp)
            for folder in ("Services", "Agents", "Sunna"):
                (vault / folder).mkdir()
            (vault / "Services" / "orchestrator.md").write_text(
                "# service\n\n[[Sunna]]\n", encoding="utf-8")
            (vault / "Agents" / "orchestrator.md").write_text(
                "# agent\n\n[[Sunna]]\n", encoding="utf-8")
            (vault / "Sunna" / "Sunna.md").write_text(
                "# Sunna\n\n[[orchestrator]] et [[Agents/orchestrator]]\n", encoding="utf-8")
            with mock.patch.object(graph, "VAULT", vault):
                stats = graph.deduplicate_note_names()
                files, by_stem, ids = graph._note_index()
                nodes, edges = graph.parse_vault()
            self.assertEqual(stats["renamed"], 1)
            self.assertEqual(len(by_stem), len(files))
            self.assertTrue((vault / "Agents" / "Agents-orchestrator.md").exists())
            self.assertTrue(all(e["to"] in {n["id"] for n in nodes} for e in edges))
            text = (vault / "Sunna" / "Sunna.md").read_text(encoding="utf-8")
            self.assertIn("[[Services/orchestrator]]", text)
            self.assertIn("[[Agents-orchestrator]]", text)

    def test_graph_header_counts_match_the_parsed_graph(self):
        html = (builder.VAULT / "graph.html").read_text(encoding="utf-8")
        nodes, edges = graph.parse_vault()
        self.assertIn(f"<b>{len(nodes)}</b> notes", html)
        self.assertIn(f"<b>{len(edges)}</b> links", html)

    def test_render_html_never_falls_back_to_a_cdn(self):
        with mock.patch.object(graph, "VENDOR_JS", Path(tempfile.gettempdir()) / "no-vis.js"):
            script = graph._vis_script()
        self.assertNotIn("http", script)
        self.assertIn("<script>", script)


if __name__ == "__main__":
    unittest.main()
