"""J140 — le cache vocal KV ne cible que le runtime llama local (11435)."""
from __future__ import annotations

from pathlib import Path

from atulya.server import create_app, voice_prefix_enabled
from atulya.settings import Settings


def _settings(root: Path, provider: str, base_url: str = "") -> Settings:
    return Settings(
        assistant_name="Atulya", host="127.0.0.1", port=8501,
        data_dir=root / "data", models_dir=root / "models",
        model_provider=provider, model_name="dolphin3", model_base_url=base_url,
        model_api_key="",
    )


def test_prefix_autorise_seulement_le_runtime_llama_local(project_temp_dir: Path) -> None:
    (project_temp_dir / "models" / "chat").mkdir(parents=True)
    assert voice_prefix_enabled(_settings(project_temp_dir, "local"))
    assert voice_prefix_enabled(_settings(project_temp_dir, "local", "http://127.0.0.1:11435/v1"))


def test_prefix_ignore_le_gateway_openai_compatible(project_temp_dir: Path) -> None:
    (project_temp_dir / "models" / "chat").mkdir(parents=True)
    assert not voice_prefix_enabled(
        _settings(project_temp_dir, "openai-compatible", "http://127.0.0.1:31416/v1")
    )


def test_prefix_sans_model_local_reste_desactive(project_temp_dir: Path) -> None:
    assert not voice_prefix_enabled(_settings(project_temp_dir, "local"))


def test_create_app_expose_le_drapeau(project_temp_dir: Path) -> None:
    (project_temp_dir / "models" / "chat").mkdir(parents=True)
    app = create_app(_settings(project_temp_dir, "openai-compatible", "http://127.0.0.1:31416/v1"))
    assert app.state.voice_prefix_enabled is False
