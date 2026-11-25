"""J73 — le contexte du cerveau local doit accepter le prompt OpenCode (~32k tokens)."""

import json
import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

import local_brain  # noqa: E402

CONFIG = Path.home() / ".config" / "opencode" / "opencode.json"
REQUEST_TOKENS = 32431  # taille réelle observée dans l'erreur de l'utilisateur


class LocalBrainContextTest(unittest.TestCase):
    def test_context_is_large_enough_for_opencode(self):
        self.assertGreaterEqual(local_brain.CONTEXT_TOKENS, REQUEST_TOKENS + 8192)

    def test_server_command_uses_one_slot_and_quantized_kv(self):
        cmd = local_brain.build_cmd(local_brain.CATALOG[0])
        self.assertEqual(cmd[cmd.index("-c") + 1], str(local_brain.CONTEXT_TOKENS))
        self.assertEqual(cmd[cmd.index("-np") + 1], "1")
        self.assertEqual(cmd[cmd.index("-ctk") + 1], local_brain.KV_CACHE_TYPE)
        self.assertEqual(cmd[cmd.index("-ctv") + 1], local_brain.KV_CACHE_TYPE)
        self.assertEqual(cmd[cmd.index("-t") + 1], str(local_brain.THREADS))
        self.assertEqual(cmd[cmd.index("-tb") + 1], str(local_brain.THREADS))
        self.assertIn("-fa", cmd)
        self.assertGreaterEqual(local_brain.CHAT_TIMEOUT, 600)

    def test_chat_queue_is_bounded_for_single_slot_server(self):
        self.assertGreaterEqual(local_brain.MAX_CONCURRENT_CHATS, 1)
        self.assertLessEqual(local_brain.MAX_CONCURRENT_CHATS, 2)
        self.assertLessEqual(local_brain.CHAT_QUEUE_TIMEOUT, 10)

    def test_opencode_declares_a_context_the_local_server_can_honor(self):
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        local = cfg["provider"]["esprieather"]
        for model in local["models"].values():
            limit = model["limit"]
            self.assertGreaterEqual(limit["context"], REQUEST_TOKENS)
            self.assertLessEqual(limit["context"] + limit["output"], local_brain.CONTEXT_TOKENS)


if __name__ == "__main__":
    unittest.main()
