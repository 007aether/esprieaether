"""J92 — garde de sortie inspirée de HN #3/#8/#18/#21 : loopback d'abord, jamais de SSRF."""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

from egress_guard import assert_loopback_url, is_loopback_url, is_public_https_url  # noqa: E402


class EgressGuardTest(unittest.TestCase):
    def test_loopback_urls_are_recognised(self) -> None:
        for url in ("http://127.0.0.1:31416/v1", "http://localhost:11434", "http://[::1]:8080/"):
            with self.subTest(url=url):
                self.assertTrue(is_loopback_url(url))

    def test_non_loopback_urls_are_not_local(self) -> None:
        for url in ("http://192.168.1.10:11434", "http://10.0.0.1", "http://api.example.com"):
            with self.subTest(url=url):
                self.assertFalse(is_loopback_url(url))

    def test_assert_loopback_url_normalises_and_accepts_local(self) -> None:
        self.assertEqual(assert_loopback_url("http://127.0.0.1:31416/"), "http://127.0.0.1:31416")

    def test_assert_loopback_url_refuses_remote_or_secret_bearing_urls(self) -> None:
        for url in (
            "http://api.example.com/v1",
            "http://192.168.1.10:11434",
            "http://user:pw@127.0.0.1:31416",
            "https://127.0.0.1:31416",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    assert_loopback_url(url)

    def test_public_https_is_allowed_for_website_buttons(self) -> None:
        self.assertTrue(is_public_https_url("https://news.ycombinator.com/"))
        self.assertTrue(is_public_https_url("https://example.com/path"))

    def test_private_or_loopback_https_is_refused(self) -> None:
        for url in (
            "https://127.0.0.1/",
            "https://localhost/",
            "https://[::1]/",
            "https://192.168.1.10/",
            "https://10.0.0.1/admin",
            "https://intranet.local/",
        ):
            with self.subTest(url=url):
                self.assertFalse(is_public_https_url(url))

    def test_query_fragment_credentials_and_http_are_refused(self) -> None:
        for url in (
            "http://example.com/",
            "https://user:pw@example.com/",
            "https://example.com/?p=2",
            "https://example.com/#top",
        ):
            with self.subTest(url=url):
                self.assertFalse(is_public_https_url(url))


if __name__ == "__main__":
    unittest.main()
