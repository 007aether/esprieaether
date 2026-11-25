"""TDD : téléchargement local résilient (Range + reprise + SHA-256)."""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

import model_manager  # noqa: E402


class FakeResponse:
    def __init__(self, data, start, total, status, fail_after=None):
        self._data = data
        self._offset = 0
        self._start = start
        self._total = total
        self.status = status
        self.headers = {"Content-Range": f"bytes {start}-{total - 1}/{total}"}
        self._fail_after = fail_after
        self._reads = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, size):
        if self._fail_after is not None and self._reads >= self._fail_after:
            raise OSError("simulated read timeout")
        self._reads += 1
        chunk = self._data[self._offset:self._offset + size]
        self._offset += len(chunk)
        return chunk


class ResilientDownloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.target = self.dir / "model.gguf"
        self.payload = bytes(range(256)) * 40  # 10 240 octets
        self.sha = hashlib.sha256(self.payload).hexdigest()

    def tearDown(self):
        self.tmp.cleanup()

    def _fake_urlopen(self, calls, fail_first=False):
        def fake(request, timeout=None):
            header = request.get_header("Range")
            start = int(header.split("=")[1].split("-")[0]) if header else 0
            calls.append(start)
            fail_after = 2 if (fail_first and not any(c == 0 for c in calls[:-1])) else None
            # Le premier appel échoue après 2 lectures ; la reprise réussit.
            if fail_first and start == 0 and len(calls) == 1:
                fail_after = 2
            return FakeResponse(self.payload[start:], start, len(self.payload),
                                206 if start else 200, fail_after)
        return fake

    def test_resume_after_timeout_and_verify_sha(self):
        calls = []
        with patch.object(model_manager, "urlopen", side_effect=self._fake_urlopen(calls, True)):
            path = model_manager.resilient_download(
                "https://example.invalid/model.gguf", self.target, self.sha,
                chunk_size=1024, max_attempts=5)
        self.assertEqual(path, self.target)
        self.assertEqual(self.target.read_bytes(), self.payload)
        self.assertFalse(self.target.with_suffix(".gguf.part").exists())
        self.assertEqual(calls[0], 0)
        self.assertGreater(calls[-1], 0)

    def test_sha_mismatch_keeps_part_and_raises(self):
        calls = []
        with patch.object(model_manager, "urlopen", side_effect=self._fake_urlopen(calls)):
            with self.assertRaises(ValueError):
                model_manager.resilient_download(
                    "https://example.invalid/model.gguf", self.target, "0" * 64,
                    chunk_size=1024, max_attempts=5)
        self.assertTrue(self.target.with_suffix(".gguf.part").is_file())
        self.assertFalse(self.target.exists())

    def test_existing_verified_file_is_not_downloaded(self):
        self.target.write_bytes(self.payload)
        with patch.object(model_manager, "urlopen", side_effect=AssertionError("réseau appelé")):
            path = model_manager.resilient_download(
                "https://example.invalid/model.gguf", self.target, self.sha)
        self.assertEqual(path, self.target)


if __name__ == "__main__":
    unittest.main()
