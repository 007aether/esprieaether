"""FreeLLMAPI en premier, cerveau GGUF local en repli automatique (J150)."""
from atulya import server
from atulya.settings import Settings


def _settings():
    return Settings(
        assistant_name="Atulya", host="127.0.0.1", port=8501,
        data_dir="", models_dir="", model_provider="openai-compatible",
        model_name="dolphin3", model_base_url="http://127.0.0.1:31416/v1",
        model_api_key="",
    )


def test_freellm_primary_keeps_a_local_fallback(monkeypatch):
    monkeypatch.setenv("ATULYA_FREELLM_PRIMARY", "1")
    monkeypatch.setenv("ATULYA_FREELLM_BASE_URL", "http://127.0.0.1:31415/v1")
    monkeypatch.setenv("ATULYA_FREELLM_MODEL", "gemini-flash-lite")
    monkeypatch.setenv("FREELLMAPI_KEY", "local-test-key")

    brain = server._make_brain(_settings())
    assert brain is not None
    provider = brain._provider
    assert provider.__class__.__name__ == "AutomaticProvider"
    primary = provider._providers[0]
    assert primary._base_url == "http://127.0.0.1:31415/v1"
    assert primary._model == "gemini-flash-lite"
    assert primary._api_key == "local-test-key"
    fallback = provider._local_provider
    assert fallback._base_url == "http://127.0.0.1:31416/v1"
    assert fallback._max_tokens == 24
    assert provider._hedge_delay > 0
    # « auto » a mis ~4,3 s au test réel : ne pas abandonner avant 6 s.
    assert provider._attempt_timeout >= 6
    assert provider._provider_budget <= 8


def test_default_model_is_auto_router(monkeypatch):
    monkeypatch.setenv("ATULYA_FREELLM_PRIMARY", "1")
    monkeypatch.delenv("ATULYA_FREELLM_MODEL", raising=False)
    brain = server._make_brain(_settings())
    assert brain._provider._providers[0]._model == "auto"


def test_local_only_when_flag_is_off(monkeypatch):
    monkeypatch.delenv("ATULYA_FREELLM_PRIMARY", raising=False)
    brain = server._make_brain(_settings())
    assert brain is not None
    assert brain._provider.__class__.__name__ == "OpenAICompatibleProvider"
    assert brain._provider._base_url == "http://127.0.0.1:31416/v1"


def test_key_file_is_read_without_exposing_it(monkeypatch, tmp_path):
    key_file = tmp_path / "freellmapi.key"
    key_file.write_text("cle-de-test\n", encoding="utf-8")
    monkeypatch.setenv("ATULYA_FREELLM_PRIMARY", "1")
    monkeypatch.setenv("ATULYA_FREELLM_KEY_FILE", str(key_file))
    monkeypatch.delenv("FREELLMAPI_KEY", raising=False)

    brain = server._make_brain(_settings())
    assert brain._provider._providers[0]._api_key == "cle-de-test"
