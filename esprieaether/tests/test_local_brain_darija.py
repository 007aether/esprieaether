"""J77 — قاعدة اللغة مفروضة على :31416 حتى للـ clients اللي ما بعتوش system prompt."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))


class DarijaPolicyTest(unittest.TestCase):
    def test_inserts_system_message_when_missing(self):
        import local_brain

        body = {"model": "dolphin3", "messages": [{"role": "user", "content": "salam"}]}
        out = local_brain.apply_language_policy(dict(body))
        self.assertEqual(out["messages"][0]["role"], "system")
        self.assertIn("arabe marocain", out["messages"][0]["content"])
        self.assertIn("lettres arabes", out["messages"][0]["content"])
        self.assertIn("aucune lettre latine", out["messages"][0]["content"])
        self.assertEqual(out["messages"][-1], body["messages"][0])

    def test_prepends_to_existing_system_without_replacing_it(self):
        import local_brain

        original = "You are a helpful coding assistant."
        body = {"messages": [
            {"role": "system", "content": original},
            {"role": "user", "content": "kifach ndir?"},
        ]}
        out = local_brain.apply_language_policy(body)
        self.assertIn("arabe marocain", out["messages"][0]["content"])
        self.assertIn("lettres arabes", out["messages"][0]["content"])
        self.assertIn("aucune lettre latine", out["messages"][0]["content"])
        self.assertIn(original, out["messages"][0]["content"])
        self.assertEqual(len(out["messages"]), 2)

    def test_arabic_only_prompt_still_gets_the_effective_directive(self):
        import local_brain

        # Le prompt Atulya dit « دارجة » en arabe : le routeur ne doit pas en
        # déduire que la consigne française efficace est déjà présente.
        arabic = "جاوب بالدارجة المغربية بحروف عربية، ما تبدّلش اللغة."
        body = {"messages": [
            {"role": "system", "content": arabic},
            {"role": "user", "content": "salam"},
        ]}
        out = local_brain.apply_language_policy(body)
        self.assertIn("arabe marocain", out["messages"][0]["content"])
        self.assertIn("lettres arabes", out["messages"][0]["content"])
        self.assertIn(arabic, out["messages"][0]["content"])

    def test_does_not_duplicate_on_repeated_calls(self):
        import local_brain

        body = {"messages": [{"role": "user", "content": "salam"}]}
        once = local_brain.apply_language_policy(body)
        twice = local_brain.apply_language_policy(once)
        self.assertEqual(once, twice)

    def test_env_switch_can_disable_policy(self):
        import local_brain

        body = {"messages": [{"role": "user", "content": "salam"}]}
        with patch.dict(os.environ, {"ESPRIA_FORCE_DARIJA": "0"}):
            self.assertEqual(local_brain.apply_language_policy(body), body)

    def test_no_secret_field_is_added(self):
        import local_brain

        out = local_brain.apply_language_policy({"messages": []})
        self.assertNotIn("api_key", str(out).lower())


if __name__ == "__main__":
    unittest.main()
