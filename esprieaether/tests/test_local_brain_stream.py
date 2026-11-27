"""Le routeur doit relayer les chunks SSE au fur et à mesure, pas les bufferiser."""

import json
import sys
import threading
import time
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

import local_brain  # noqa: E402


class _StreamResponse:
    status = 200

    def __init__(self, chunks, delays):
        self._chunks = iter(chunks)
        self._delays = iter(delays)
        self.read_called = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        self.read_called = True
        raise AssertionError("read() ne doit pas être appelé pour une réponse streamée")

    def readline(self):
        time.sleep(next(self._delays, 0))
        return next(self._chunks, b"")


class LocalBrainStreamTest(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), local_brain.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_sse_chunks_arrive_before_the_stream_ends(self):
        first = b'data: {"choices":[{"delta":{"content":"salam"}}]}\n\n'
        done = b"data: [DONE]\n\n"
        response = _StreamResponse([first, done], [0.05, 0.45])

        real_urlopen = urllib.request.urlopen

        def fake_urlopen(request, timeout=None):
            if ":3150" not in request.full_url:
                return real_urlopen(request, timeout=timeout)
            return response

        request = urllib.request.Request(
            self.base + "/v1/chat/completions",
            data=json.dumps({"model": "dolphin3", "stream": True,
                             "messages": [{"role": "user", "content": "salut"}]}).encode(),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with patch.object(local_brain, "available_models", return_value=local_brain.CATALOG), \
             patch.object(local_brain, "ensure_active", return_value=True), \
             patch.object(local_brain.urllib.request, "urlopen", side_effect=fake_urlopen):
            started = time.monotonic()
            with urllib.request.urlopen(request, timeout=10) as resp:
                self.assertNotIn("Content-Length", dict(resp.headers))
                first_line = resp.readline()
                first_ms = (time.monotonic() - started) * 1000
                rest = resp.read()
                total_ms = (time.monotonic() - started) * 1000

        self.assertIn(b'"content":"salam"', first_line)
        self.assertIn(b"[DONE]", rest)
        self.assertLess(first_ms, 350, f"premier chunk trop tardif: {first_ms:.0f}ms")
        self.assertGreater(total_ms - first_ms, 300, "les chunks n'ont pas été relayés progressivement")
        self.assertFalse(response.read_called)
