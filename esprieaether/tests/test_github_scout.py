"""J94 — github_scout : collecte GitHub seule, sans secret et sans réseau dans les tests."""

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

import github_scout  # noqa: E402
from github_scout import allowed, harvest, run  # noqa: E402


def _repo(name, description="", **extra):
    item = {
        "full_name": name,
        "description": description,
        "html_url": "https://github.com/" + name,
    }
    item.update(extra)
    return item


def _page_fetcher(names):
    calls = []

    def fetcher(query, page, per_page):
        calls.append((query, page, per_page))
        start = (page - 1) * per_page
        return {"items": [_repo(name, "وصف " + name) for name in names[start:start + per_page]]}

    return fetcher, calls


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b'{"items": []}'


class GithubScoutTest(unittest.TestCase):
    def test_harvest_collects_1000_unique_from_10_pages(self):
        names = ["org/repo-%04d" % i for i in range(1000)]
        calls = []

        def fetcher(query, page, per_page):
            calls.append((query, page, per_page))
            start = (page - 1) * per_page
            items = [_repo(name, "وصف " + name) for name in names[start:start + per_page]]
            if page > 1:  # doublon volontaire : ne doit jamais compter deux fois
                items.append(_repo(names[0], "مكرر"))
            return {"items": items}

        result = harvest(fetcher, queries=["ai agent framework"])

        self.assertEqual(result["scanned"], 1000)
        self.assertEqual(result["status"], "live_verified")
        self.assertEqual([call[1] for call in calls], list(range(1, 11)))
        self.assertTrue(all(call[2] == 100 for call in calls))
        self.assertEqual(set(call[0] for call in calls), {"ai agent framework"})

    def test_smaller_limit_stops_early(self):
        names = ["org/small-%04d" % i for i in range(1000)]
        fetcher, calls = _page_fetcher(names)

        result = harvest(fetcher, limit=250, queries=["local llm"])

        self.assertEqual(result["scanned"], 250)
        self.assertEqual(len(calls), 3)

    def test_secrets_and_query_urls_are_scrubbed(self):
        description = (
            "api_key=SUPERSECRET_ABC token=TOKEN_XYZ password=PWD_XYZ secret=SECRET_XYZ "
            + "وصف طويل " * 60
        )
        unsafe = _repo(
            "org/unsafe",
            description,
            html_url="https://github.com/org/unsafe?token=TOKEN_XYZ#frag",
        )

        def fetcher(query, page, per_page):
            return {"items": [unsafe] if page == 1 else []}

        with tempfile.TemporaryDirectory() as tmp:
            result = run(state_dir=tmp, fetcher=fetcher, limit=10)
            report_path = Path(tmp) / "github_scout_report.json"
            raw = report_path.read_text(encoding="utf-8")

        for needle in ("SUPERSECRET_ABC", "TOKEN_XYZ", "PWD_XYZ", "SECRET_XYZ", "#frag"):
            self.assertNotIn(needle, raw)
        for marker in ("api_key=", "token=", "password=", "secret=", "?", "#"):
            self.assertNotIn(marker, raw)
        self.assertIn("org/unsafe", raw)
        self.assertLessEqual(len(result["sample"][0]["description"]), 200)

    def test_allowed_only_accepts_exact_github_api_host(self):
        self.assertTrue(
            allowed("https://api.github.com/search/repositories?q=local+llm")["allowed"]
        )
        for url in (
            "http://127.0.0.1/x",
            "https://example.com/x",
            "https://api.github.com.evil.example/x",
        ):
            with self.subTest(url=url):
                self.assertFalse(allowed(url)["allowed"])

    def test_empty_fetcher_reports_no_data_source(self):
        result = harvest(lambda query, page, per_page: {"items": []},
                         queries=["self improving agent"])

        self.assertEqual(result["status"], "no_data_source")
        self.assertEqual(result["scanned"], 0)
        self.assertNotEqual(result["status"], "live_verified")

    def test_run_writes_report_with_valid_timestamp_and_bounded_sample(self):
        names = ["org/voice-%04d" % i for i in range(100)]
        fetcher, _calls = _page_fetcher(names)

        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            result = run(state_dir=state_dir, fetcher=fetcher, limit=1000)
            report_path = state_dir / "github_scout_report.json"
            self.assertTrue(report_path.is_file())
            raw = report_path.read_text(encoding="utf-8")
        data = json.loads(raw)

        self.assertEqual(data, result)
        for key in ("ok", "status", "checked_at", "target", "scanned", "queries",
                    "topics", "languages", "sample", "next"):
            self.assertIn(key, data)
        parsed = datetime.fromisoformat(data["checked_at"].replace("Z", "+00:00"))
        self.assertIsNotNone(parsed.tzinfo)
        self.assertEqual(data["target"], "https://api.github.com")
        self.assertEqual(data["scanned"], 100)
        self.assertLessEqual(len(data["sample"]), 20)
        self.assertTrue(data["sample"])

    def test_default_fetcher_checks_policy_before_request(self):
        seen = []
        original_check = github_scout.policy_gate.check_url

        def spy(url, **kwargs):
            seen.append((url, kwargs))
            return original_check(url, **kwargs)

        with patch.object(github_scout.policy_gate, "check_url", side_effect=spy), \
                patch.object(github_scout.urllib.request, "urlopen",
                             return_value=_FakeResponse()) as urlopen:
            payload = github_scout._default_fetcher("local llm", 1, 100)

        self.assertEqual(payload, {"items": []})
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0][1], {"action": "research", "internet": True})
        self.assertEqual(urlopen.call_count, 1)


if __name__ == "__main__":
    unittest.main()
