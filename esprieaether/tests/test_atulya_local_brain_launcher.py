"""J79: le lanceur Atulya doit utiliser uniquement le cerveau local."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "START_ATULYA_TANTRA.cmd"


class AtulyaLocalBrainLauncherTest(unittest.TestCase):
    def test_launcher_forces_local_brain(self) -> None:
        cmd = LAUNCHER.read_text(encoding="utf-8")
        self.assertIn('set "ATULYA_MODEL_PROVIDER=openai-compatible"', cmd)
        self.assertIn('set "ATULYA_MODEL_BASE_URL=http://127.0.0.1:31416/v1"', cmd)
        self.assertIn('set "ATULYA_MODEL_NAME=dolphin3"', cmd)
        self.assertIn('set "ATULYA_MODEL_TIMEOUT=120"', cmd)
        self.assertIn('set "ATULYA_FORCE_DARIJA=1"', cmd)

    def test_vendored_persona_injects_darija_policy(self) -> None:
        import importlib.util
        import os

        persona_path = ROOT / "GITHUB_IMPORT" / "Atulya-Tantra" / "atulya" / "persona.py"
        source = persona_path.read_text(encoding="utf-8")
        self.assertIn('ATULYA_FORCE_DARIJA', source)
        spec = importlib.util.spec_from_file_location("atulya_persona_probe", persona_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        previous = os.environ.get('ATULYA_FORCE_DARIJA')
        os.environ['ATULYA_FORCE_DARIJA'] = '1'
        try:
            prompt = module.build_system_prompt('Atulya')
        finally:
            if previous is None:
                os.environ.pop('ATULYA_FORCE_DARIJA', None)
            else:
                os.environ['ATULYA_FORCE_DARIJA'] = previous
        self.assertIn('arabe marocain', prompt.lower())
        self.assertIn('lettres arabes', prompt.lower())

    def test_vendored_provider_accepts_timeout_override(self) -> None:
        providers = ROOT / "GITHUB_IMPORT" / "Atulya-Tantra" / "tools" / "plugins" / "brain" / "providers.py"
        source = providers.read_text(encoding="utf-8")
        self.assertIn('ATULYA_MODEL_TIMEOUT', source)

    def test_supervisor_manages_atulya_on_loopback(self) -> None:
        supervisor = ROOT / "esprieaether" / "scripts" / "keep_alive.ps1"
        source = supervisor.read_text(encoding="utf-8")
        self.assertIn("Name='atulya'", source)
        self.assertIn('Port=8501', source)
        self.assertIn("'-m','atulya.cli','serve'", source)
        for key in (
            "PYTHONPATH",
            "ATULYA_DATA_DIR",
            "ATULYA_MODEL_PROVIDER",
            "ATULYA_MODEL_NAME",
            "ATULYA_MODEL_BASE_URL",
            "ATULYA_MODEL_TIMEOUT",
            "ATULYA_FORCE_DARIJA",
        ):
            self.assertIn(key + "=", source)
        self.assertIn("8501 = '/api/health'", source)

    def test_startup_shortcut_delegates_to_supervisor(self) -> None:
        starter = ROOT / "esprieaether" / "start_esprieaether_247.ps1"
        self.assertTrue(starter.is_file(), "start_esprieaether_247.ps1 is missing from startup")
        self.assertIn("keep_alive.ps1", starter.read_text(encoding="utf-8"))

    def test_selftest_avoids_duplicate_cookie_lookup(self) -> None:
        source = (ROOT / "GITHUB_IMPORT" / "Atulya-Tantra" / "tools" / "selftest.py").read_text(encoding="utf-8")
        self.assertIn("def _cookie_value", source)
        self.assertNotIn('.cookies.get("atulya_session")', source)

    def test_launcher_has_no_cloud_provider_or_secret(self) -> None:
        cmd = LAUNCHER.read_text(encoding="utf-8")
        self.assertIsNone(re.search(
            r"OPENROUTER_API_KEY|NVIDIA_API_KEY|GEMINI_API_KEY|DEEPSEEK_API_KEY|sk-[A-Za-z0-9]",
            cmd,
            re.IGNORECASE,
        ))


if __name__ == "__main__":
    unittest.main()
