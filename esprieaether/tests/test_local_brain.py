"""Le routeur local expose 3 modèles GGUF sans clé ni dépendance externe."""

import json
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

import local_brain  # noqa: E402


class _Response:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b'{"choices":[{"message":{"content":"PONG"}}]}'


class LocalBrainTest(unittest.TestCase):
    def test_catalog_has_three_uncensored_models_on_distinct_ports(self):
        self.assertEqual(len(local_brain.CATALOG), 3)
        ports = [m["port"] for m in local_brain.CATALOG]
        self.assertEqual(len(set(ports)), 3)
        for model in local_brain.CATALOG:
            self.assertTrue(model["file"].endswith(".gguf"))
            self.assertTrue(model["id"])
            self.assertTrue(model["label"])
            self.assertGreater(model["bytes"], 1_000_000_000)

    def test_catalog_filenames_match_download_script(self):
        """Un nom de fichier erroné donne un 404 HF : le script et le routeur doivent concorder."""
        script = (BASE_DIR / "scripts" / "download_local_models.ps1").read_text(encoding="utf-8")
        for model in local_brain.CATALOG:
            filename = model["file"]
            self.assertIn("name = '%s'" % filename, script)
            self.assertIn("/resolve/main/%s'" % filename, script)

    def test_only_complete_files_are_advertised(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            small = dict(local_brain.CATALOG[0], bytes=1024)
            (root / small["file"]).write_bytes(b"x" * 512)
            with patch.object(local_brain, "MODELS_DIR", root), \
                 patch.object(local_brain, "CATALOG", [small]):
                self.assertEqual(local_brain.available_models(), [])
            (root / small["file"]).write_bytes(b"x" * 2048)
            with patch.object(local_brain, "MODELS_DIR", root), \
                 patch.object(local_brain, "CATALOG", [small]):
                self.assertEqual([m["id"] for m in local_brain.available_models()],
                                 [small["id"]])

    def test_requested_model_wins_and_default_is_used_otherwise(self):
        models = local_brain.CATALOG
        self.assertEqual(local_brain.select_model("hermes3", models)["id"], "hermes3")
        self.assertEqual(local_brain.select_model(None, models)["id"], local_brain.DEFAULT_MODEL)
        self.assertEqual(local_brain.select_model("inconnu", models)["id"], local_brain.DEFAULT_MODEL)

    def test_server_command_stays_on_loopback_and_cpu(self):
        cmd = local_brain.build_cmd(local_brain.CATALOG[0])
        self.assertIn("127.0.0.1", cmd)
        self.assertIn("llama-server.exe", " ".join(cmd))
        self.assertIn("--n-gpu-layers", cmd)
        self.assertIn(str(local_brain.CATALOG[0]["port"]), cmd)

    def _start(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), local_brain.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, f"http://127.0.0.1:{server.server_port}"

    @staticmethod
    def _get(url):
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read())

    def test_health_and_models_endpoints(self):
        server, base = self._start()
        try:
            with patch.object(local_brain, "available_models", return_value=local_brain.CATALOG[:2]):
                health = self._get(base + "/health")
                models = self._get(base + "/v1/models")
            self.assertEqual(health["count"], 2)
            self.assertEqual(health["router"], "local-brain")
            self.assertEqual([m["id"] for m in models["data"]], ["dolphin3", "hermes3"])
        finally:
            server.shutdown()
            server.server_close()

    def test_completion_routes_to_selected_local_model(self):
        captured = {}
        real_urlopen = urllib.request.urlopen

        def fake_urlopen(request, timeout=None):
            if ":3150" not in request.full_url:
                return real_urlopen(request, timeout=timeout)
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data)
            return _Response()

        server, base = self._start()
        try:
            with patch.object(local_brain, "available_models", return_value=local_brain.CATALOG), \
                 patch.object(local_brain, "ensure_active", return_value=True), \
                 patch.object(local_brain.urllib.request, "urlopen", side_effect=fake_urlopen):
                request = urllib.request.Request(
                    base + "/v1/chat/completions",
                    data=json.dumps({"model": "hermes3", "messages": [{"role": "user", "content": "salut"}]}).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=10) as resp:
                    body = json.loads(resp.read())
            self.assertIn(":31502/v1/chat/completions", captured["url"])
            self.assertEqual(captured["body"]["model"], "hermes3")
            self.assertEqual(body["choices"][0]["message"]["content"], "PONG")
        finally:
            server.shutdown()
            server.server_close()

    def test_missing_model_is_honest_503(self):
        server, base = self._start()
        try:
            with patch.object(local_brain, "available_models", return_value=[]):
                req = urllib.request.Request(
                    base + "/v1/chat/completions",
                    data=json.dumps({"messages": []}).encode(),
                    headers={"Content-Type": "application/json"}, method="POST")
                try:
                    urllib.request.urlopen(req, timeout=10)
                    self.fail("modèle absent devait être refusé")
                except urllib.error.HTTPError as exc:
                    self.assertEqual(exc.code, 503)
                    self.assertIn("no local model installed", exc.read().decode("utf-8"))
                    exc.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_busy_slot_returns_429_not_fake_unavailable(self):
        entered = threading.Event()
        release = threading.Event()
        real_urlopen = urllib.request.urlopen

        def slow_urlopen(request, timeout=None):
            if ":3150" not in request.full_url:
                return real_urlopen(request, timeout=timeout)
            entered.set()
            release.wait(5)
            return _Response()

        server, base = self._start()
        first = {}
        try:
            with patch.object(local_brain, "available_models", return_value=local_brain.CATALOG), \
                 patch.object(local_brain, "ensure_active", return_value=True), \
                 patch.object(local_brain, "chat_slots", threading.BoundedSemaphore(1)), \
                 patch.object(local_brain, "CHAT_QUEUE_TIMEOUT", 1), \
                 patch.object(local_brain.urllib.request, "urlopen", side_effect=slow_urlopen):
                def run_first():
                    req = urllib.request.Request(
                        base + "/v1/chat/completions",
                        data=json.dumps({"messages": [{"role": "user", "content": "un"}]}).encode(),
                        headers={"Content-Type": "application/json"}, method="POST")
                    try:
                        with urllib.request.urlopen(req, timeout=10) as resp:
                            first["status"] = resp.status
                    except Exception as exc:
                        first["error"] = str(exc)

                thread = threading.Thread(target=run_first, daemon=True)
                thread.start()
                self.assertTrue(entered.wait(5), "premier appel jamais entré")
                req2 = urllib.request.Request(
                    base + "/v1/chat/completions",
                    data=json.dumps({"messages": [{"role": "user", "content": "deux"}]}).encode(),
                    headers={"Content-Type": "application/json"}, method="POST")
                try:
                    urllib.request.urlopen(req2, timeout=10)
                    self.fail("deuxième appel aurait dû être refusé")
                except urllib.error.HTTPError as exc:
                    self.assertEqual(exc.code, 429)
                    self.assertTrue(exc.headers.get("Retry-After"))
                    self.assertIn("busy", exc.read().decode("utf-8"))
                    exc.close()
                finally:
                    release.set()
                    thread.join(5)
            self.assertEqual(first.get("status"), 200, first)
        finally:
            release.set()
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
