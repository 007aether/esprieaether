"""J152 — TDD : جلب 20 مشروعاً مفيداً من تقرير آخر 7 أيام، بتنزيل محلي معزول."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import github_projects  # noqa: E402


WEEK_ITEMS = [
    {"name": "w01fb0ss/PiBot", "url": "https://github.com/w01fb0ss/PiBot",
     "description": "local-first AI agents, MCP, routines", "stars": 620, "pushed_at": "2026-11-26T00:00:00Z"},
    {"name": "sous-labs/songe", "url": "https://github.com/sous-labs/songe",
     "description": "training engine for your local model", "stars": 877, "pushed_at": "2026-11-26T00:00:00Z"},
    {"name": "enwove/flyx", "url": "https://github.com/enwove/flyx",
     "description": "zero-dependency local LLM inference engine", "stars": 43, "pushed_at": "2026-11-26T00:00:00Z"},
    {"name": "setyamickala/airdrop-agent", "url": "https://github.com/setyamickala/airdrop-agent",
     "description": "airdrop wallets and testnets", "stars": 104, "pushed_at": "2026-11-26T00:00:00Z"},
    {"name": "wc4440222/google-ai-offer-subscription", "url": "https://github.com/wc4440222/google-ai-offer-subscription",
     "description": "rooted Android emulator billing", "stars": 104, "pushed_at": "2026-11-26T00:00:00Z"},
]


class GithubProjectsTest(unittest.TestCase):
    def test_selection_is_capped_at_twenty_and_skips_risky_repos(self) -> None:
        picked = github_projects.select(WEEK_ITEMS, limit=20)
        self.assertEqual(len(picked), 3)
        names = {row["name"] for row in picked}
        self.assertEqual(names, {"w01fb0ss/PiBot", "sous-labs/songe", "enwove/flyx"})
        self.assertTrue(all(row["url"].startswith("https://github.com/") for row in picked))

    def test_selection_accepts_any_useful_repo_to_reach_twenty(self) -> None:
        items = [
            {"name": f"owner/repo-{index}", "url": f"https://github.com/owner/repo-{index}",
             "description": "local voice assistant with offline tools", "stars": index}
            for index in range(25)
        ]
        picked = github_projects.select(items, limit=20)
        self.assertEqual(len(picked), 20)
        self.assertEqual(len({row["name"] for row in picked}), 20)

    def test_clone_command_is_shallow_and_has_no_install_hooks(self) -> None:
        cmd = github_projects.clone_command("git.exe", "https://github.com/owner/repo", Path("dest"))
        self.assertEqual(cmd[:2], ["-c", "safe.directory=*"])
        self.assertIn("clone", cmd)
        self.assertIn("--depth", cmd)
        self.assertIn("1", cmd)
        self.assertNotIn("--recurse-submodules", cmd)
        self.assertNotIn("pip", " ".join(cmd))
        self.assertNotIn("npm", " ".join(cmd))
        self.assertEqual(cmd[-2], "https://github.com/owner/repo")
        self.assertEqual(cmd[-1], str(Path("dest")))

    def test_report_uses_only_allowed_statuses_and_fresh_timestamps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            report = github_projects.write_report(
                state,
                [{"name": "owner/repo", "url": "https://github.com/owner/repo", "reason": "local first"}],
                [{"name": "owner/repo", "status": "live_verified", "detail": "cloned"}],
            )
            path = state / "github_projects_report.json"
            self.assertTrue(path.exists())
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), report)
            self.assertEqual(report["status"], "live_verified")
            self.assertEqual(report["projects"][0]["status"], "live_verified")
            self.assertIn("checkedAt", report)

    def test_non_github_url_is_rejected_before_any_clone(self) -> None:
        with self.assertRaises(ValueError):
            github_projects.clone_command("git.exe", "http://evil.invalid/repo", Path("dest"))


if __name__ == "__main__":
    unittest.main()
