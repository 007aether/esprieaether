"""Atulya starts on the local JARVIS HUD; its WebUI routes stay reachable."""
import asyncio

import httpx
import pytest

from atulya.server import create_app
from atulya.settings import Settings

LANDING = "http://127.0.0.1:3860/jarvis.html"


def _settings(tmp_path, landing_url=""):
    return Settings(
        assistant_name="Atulya", host="127.0.0.1", port=8501,
        data_dir=tmp_path / "data", models_dir=tmp_path / "models",
        model_provider="", model_name="", model_base_url="", model_api_key="",
        landing_url=landing_url,
    )


def test_landing_url_defaults_to_empty(tmp_path):
    assert _settings(tmp_path).landing_url == ""


@pytest.mark.parametrize("bad", [
    "http://localhost:3860/jarvis.html",
    "http://127.0.0.2:3860/jarvis.html",
    "https://example.org/jarvis.html",
    "http://127.0.0.1:3860/jarvis.html?x=1",
    "http://127.0.0.1:3860/jarvis.html#f",
    "http://u:p@127.0.0.1:3860/jarvis.html",
    "file:///jarvis.html",
])
def test_landing_url_rejects_remote_or_tricky_targets(tmp_path, bad):
    with pytest.raises(ValueError):
        _settings(tmp_path, bad)


def test_landing_url_is_read_from_environment(monkeypatch):
    monkeypatch.setenv("ATULYA_LANDING_URL", LANDING)
    assert Settings.from_environment().landing_url == LANDING


def test_root_redirects_to_hud_and_webui_stays_local(tmp_path):
    app = create_app(_settings(tmp_path, LANDING))

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                     base_url="http://127.0.0.1:8501") as client:
            redirected = await client.get("/", follow_redirects=False)
            assert redirected.status_code == 302
            assert redirected.headers["location"] == LANDING
            index = await client.get("/index.html")
            assert index.status_code == 200
            assert "system-dashboard" in index.text

    asyncio.run(exercise())


def test_root_serves_webui_without_a_landing_url(tmp_path):
    app = create_app(_settings(tmp_path))

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                     base_url="http://127.0.0.1:8501") as client:
            page = await client.get("/")
            assert page.status_code == 200
            assert "system-dashboard" in page.text

    asyncio.run(exercise())
