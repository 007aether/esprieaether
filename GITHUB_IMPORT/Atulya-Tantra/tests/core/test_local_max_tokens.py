"""Le provider loopback limite la longueur de la réponse : 3B ≈ 4 tokens/s ici."""
from atulya import server
from atulya.settings import Settings


def _settings(base_url):
    return Settings(assistant_name="Atulya", host="127.0.0.1", port=8501,
                    data_dir="", models_dir="", model_provider="openai-compatible",
                    model_name="dolphin3", model_base_url=base_url, model_api_key="")


def test_local_provider_has_a_short_answer_budget(monkeypatch):
    monkeypatch.setenv("ATULYA_LOCAL_MAX_TOKENS", "24")
    brain = server._make_brain(_settings("http://127.0.0.1:31416/v1"))
    assert brain is not None
    assert brain._provider._max_tokens == 24


def test_external_provider_keeps_its_default_budget(monkeypatch):
    monkeypatch.delenv("ATULYA_LOCAL_MAX_TOKENS", raising=False)
    brain = server._make_brain(_settings("https://example.invalid/v1"))
    assert brain is not None
    assert brain._provider._max_tokens is None
