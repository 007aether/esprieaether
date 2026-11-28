from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "bots") not in sys.path:
    sys.path.insert(0, str(ROOT / "bots"))

import self_heal  # noqa: E402


class _Result:
    returncode = 0
    stderr = b""


def test_no_hardcoded_user_path() -> None:
    source = (ROOT / "bots" / "self_heal.py").read_text(encoding="utf-8")
    assert "ESPRIEAETHER" not in source
    assert "RedirectStandardOutput" in source
    assert "RedirectStandardError" in source
    assert source.count("-RedirectStandardOutput") == source.count("-RedirectStandardError")


def test_cloud_probe_uses_root_not_missing_health() -> None:
    assert self_heal.SERVICES["cloud"] == (5001, "")
    assert self_heal.SERVICES["jarvis"][0] == 8000


def test_ollama_missing_is_unavailable_not_fake_restart(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(self_heal, "_ollama", lambda: None)
    result = self_heal.restart_service("ollama", 11434, "api/tags")
    assert isinstance(result, str)
    assert result.startswith("unavailable:")


def test_python_resolver_prefers_local_venv() -> None:
    python = self_heal._python()
    assert python.exists()
    assert "python" in python.name.lower()


def test_jarvis_restart_uses_existing_minimal_api(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _Result()

    monkeypatch.setattr(self_heal.subprocess, "run", fake_run)
    result = self_heal.restart_service("jarvis", 8000, "docs")
    assert result is True
    assert calls
    command = calls[0][-1]
    assert "jarvis_api_minimal.py" in command
    assert "jarvis_api.py'" not in command
    assert ".out.log" in command and ".err.log" in command
