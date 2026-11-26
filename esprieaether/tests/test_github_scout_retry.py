"""J126 — TDD : la veille GitHub respecte la limite de débit sans jeton."""

import json
import sys
import unittest
import urllib.error
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import github_scout  # noqa: E402


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps({"items": [{"full_name": "owner/repo"}]}).encode("utf-8")


class GithubScoutRetryTest(unittest.TestCase):
    def test_une_limite_403_est_rejouee_apres_attente(self) -> None:
        calls = {"open": 0, "sleep": []}

        def opener(_request, timeout=10):
            calls["open"] += 1
            if calls["open"] < 3:
                raise urllib.error.HTTPError(
                    "https://api.github.com/search/repositories", 403,
                    "rate limit exceeded", {}, None)
            return _Response()

        payload = github_scout._default_fetcher(
            "local llm", 1, 100, opener=opener,
            sleeper=lambda seconds: calls["sleep"].append(seconds))
        self.assertEqual(calls["open"], 3)
        self.assertEqual(len(calls["sleep"]), 2)
        self.assertGreaterEqual(min(calls["sleep"]), 30)
        self.assertEqual(payload["items"][0]["full_name"], "owner/repo")

    def test_les_appels_sont_espaces_pour_rester_sous_la_limite(self) -> None:
        calls = {"sleep": []}
        github_scout._default_fetcher(
            "local llm", 1, 100, opener=lambda *_a, **_k: _Response(),
            sleeper=lambda seconds: calls["sleep"].append(seconds))
        self.assertTrue(calls["sleep"])
        self.assertGreaterEqual(calls["sleep"][0], 5)


if __name__ == "__main__":
    unittest.main()
