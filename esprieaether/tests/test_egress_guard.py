"""J59 — حارس الخروج للشبكة + singleton للـrobot daemon.

TDD: الاختبارات قبل ربط news_scanner / market_watcher و قبل src/singleton.py.
أي طلب شبكة أو عملية كايتدارو بـ mock.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
for part in ("src", "scanners", "robots"):
    sys.path.insert(0, str(BASE_DIR / part))


class EgressGuardTest(unittest.TestCase):
    def test_news_scanner_does_not_fetch_when_gate_denies(self):
        import news_scanner

        denied = SimpleNamespace(allowed=False, reason="private_network")
        with patch.object(news_scanner, "check_url", return_value=denied), \
             patch.object(news_scanner.requests, "get",
                          side_effect=AssertionError("must not fetch")):
            result = news_scanner.NewsScanner().fetch_feed("LAN", "http://192.168.0.113/feed")
        self.assertEqual(result, [])

    def test_news_scanner_fetch_still_works_when_gate_allows(self):
        import news_scanner

        allowed = SimpleNamespace(allowed=True, reason="internet_allowed")
        xml = b'<rss><channel><item><title>salam</title><link>http://x/</link></item></channel></rss>'
        response = SimpleNamespace(status_code=200, content=xml)
        scanner = news_scanner.NewsScanner()
        with patch.object(scanner, "init_db"), \
             patch.object(news_scanner.sqlite3, "connect"), \
             patch.object(news_scanner, "check_url", return_value=allowed), \
             patch.object(news_scanner.requests, "get", return_value=response):
            result = news_scanner.NewsScanner.fetch_feed(scanner, "OK", "https://hnrss.org/frontpage")
        self.assertEqual(result[0]["title"], "salam")

    def test_internet_probe_does_not_connect_when_gate_denies(self):
        from scripts import write_internet_status as status

        denied = SimpleNamespace(allowed=False, reason="private_network")
        with patch.object(status, "check_url", return_value=denied), \
             patch.object(status.socket, "getaddrinfo",
                          side_effect=AssertionError("must not connect")):
            result = status.probe("192.168.0.113", 443)
        self.assertFalse(result["available"])
        self.assertIn("private_network", result["reason"])

    def test_hermes_ping_does_not_call_external_endpoint_when_gate_denies(self):
        import hermes_bridge

        denied = SimpleNamespace(allowed=False, reason="private_network")
        bridge = hermes_bridge.HermesBridge()
        bridge.base_url = "http://192.168.0.113:8000/v1"
        with patch.object(hermes_bridge, "check_url", return_value=denied), \
             patch.object(hermes_bridge.urllib.request, "urlopen",
                          side_effect=AssertionError("must not call")):
            result = bridge.ping()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "private_network")

    def test_market_watcher_does_not_fetch_when_gate_denies(self):
        import market_watcher

        denied = SimpleNamespace(allowed=False, reason="private_network")
        with patch.object(market_watcher, "check_url", return_value=denied), \
             patch.object(market_watcher.requests, "get",
                          side_effect=AssertionError("must not fetch")):
            result = market_watcher.MarketWatcher().fetch_prices()
        self.assertEqual(result, {})


class SingletonTest(unittest.TestCase):
    def test_second_acquire_is_refused_while_first_is_held(self):
        from singleton import SingletonLock

        with tempfile.TemporaryDirectory() as tmp:
            first = SingletonLock("robot_daemon", tmp)
            second = SingletonLock("robot_daemon", tmp)
            self.assertTrue(first.acquire())
            self.assertFalse(second.acquire())
            first.release()

    def test_stale_pid_lock_can_be_recovered(self):
        from singleton import SingletonLock

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "robot_daemon.lock"
            path.write_text("99999999", encoding="ascii")
            lock = SingletonLock("robot_daemon", tmp)
            self.assertTrue(lock.acquire())
            lock.release()

    def test_access_denied_pid_is_treated_as_alive(self):
        import singleton

        kernel = SimpleNamespace(OpenProcess=lambda *a: 0, CloseHandle=lambda *a: None)
        fake_ctypes = SimpleNamespace(
            WinDLL=lambda *a, **k: kernel, get_last_error=lambda: 5)
        with patch.object(singleton.os, "name", "nt"), \
             patch.dict(sys.modules, {"ctypes": fake_ctypes}):
            self.assertTrue(singleton._pid_alive(4242))

    def test_missing_pid_is_treated_as_dead(self):
        import singleton

        kernel = SimpleNamespace(OpenProcess=lambda *a: 0, CloseHandle=lambda *a: None)
        fake_ctypes = SimpleNamespace(
            WinDLL=lambda *a, **k: kernel, get_last_error=lambda: 87)
        with patch.object(singleton.os, "name", "nt"), \
             patch.dict(sys.modules, {"ctypes": fake_ctypes}):
            self.assertFalse(singleton._pid_alive(4242))

    def test_daemon_refuses_to_start_a_second_instance(self):
        import robot_daemon

        fake_lock = SimpleNamespace(acquire=lambda: False, release=lambda: None)
        with patch.object(robot_daemon, "SingletonLock", return_value=fake_lock), \
             patch.object(robot_daemon.logger, "info") as info:
            robot_daemon.main()
        messages = " ".join(str(c) for c in info.call_args_list)
        self.assertIn("another instance", messages)

    def test_release_allows_a_new_acquire_and_lock_has_no_secret(self):
        from singleton import SingletonLock

        with tempfile.TemporaryDirectory() as tmp:
            lock = SingletonLock("robot_daemon", tmp)
            self.assertTrue(lock.acquire())
            blob = (Path(tmp) / "robot_daemon.lock").read_text(encoding="ascii")
            self.assertTrue(blob.strip().isdigit())
            lock.release()
            self.assertTrue(SingletonLock("robot_daemon", tmp).acquire())


if __name__ == "__main__":
    unittest.main()
