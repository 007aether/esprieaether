"""J57 — état Internet public : tests avant scripts/write_internet_status.py."""

import json
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "scripts"))


class InternetStatusTest(unittest.TestCase):
    def test_dns_failure_is_honest(self):
        import write_internet_status as mod

        with patch.object(mod.socket, "getaddrinfo",
                          side_effect=socket.gaierror("no dns")):
            result = mod.probe(host="pypi.org")
        self.assertFalse(result["available"])
        self.assertEqual(result["reason"], "dns_failed")
        self.assertEqual(result["host"], "pypi.org")

    def test_successful_tcp_connect_reports_internet(self):
        import write_internet_status as mod

        class FakeSocket:
            def __init__(self, *a):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def settimeout(self, value):
                self.timeout = value

            def connect(self, addr):
                self.addr = addr

        info = (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("151.101.0.223", 443))
        with patch.object(mod.socket, "getaddrinfo", return_value=[info]), \
             patch.object(mod.socket, "socket", return_value=FakeSocket()):
            result = mod.probe(host="pypi.org")
        self.assertTrue(result["available"])
        self.assertEqual(result["mode"], "internet")
        self.assertEqual(result["host"], "pypi.org")
        self.assertIsNone(result["reason"])

    def test_written_status_has_no_secret_field(self):
        import write_internet_status as mod

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "state" / "internet_status.json"
            payload = {"available": True, "mode": "internet", "host": "pypi.org",
                       "checkedAt": "2026-11-23T21:10:00+00:00", "reason": None}
            mod.write_status(target, payload)
            raw = target.read_text(encoding="utf-8")
        self.assertEqual(json.loads(raw), payload)
        for word in ("api_key", "token", "password", "secret"):
            self.assertNotIn(word, raw.lower())


if __name__ == "__main__":
    unittest.main()
