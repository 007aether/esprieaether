"""J140 — auth/status lit un seul snapshot SQLite au lieu de six connexions."""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
from pathlib import Path

import httpx

from atulya.auth import AuthStore, SESSION_COOKIE
from atulya.server import create_app
from atulya.settings import Settings


def _settings(root: Path) -> Settings:
    return Settings(
        assistant_name="Atulya", host="127.0.0.1", port=8501,
        data_dir=root / "data", models_dir=root / "models",
        model_provider="", model_name="", model_base_url="", model_api_key="",
    )


def test_auth_status_snapshot_ouvre_une_seule_connexion(project_temp_dir: Path) -> None:
    store = AuthStore(project_temp_dir)
    token = store.create_session()
    calls: list[int] = []
    original = store._session

    @contextmanager
    def counted():
        calls.append(1)
        with original() as db:
            yield db

    store._session = counted  # type: ignore[method-assign]
    snapshot = store.auth_status_snapshot(token)
    assert len(calls) == 1
    assert snapshot["credential_count"] == 0
    assert snapshot["password_login"] is False
    assert snapshot["user_id"] == "admin"
    assert snapshot["display_name"] == "Admin"
    assert snapshot["is_admin"] is True


def test_auth_status_snapshot_sans_session_reste_vide(project_temp_dir: Path) -> None:
    store = AuthStore(project_temp_dir)
    snapshot = store.auth_status_snapshot("invalid")
    assert snapshot["credential_count"] == 0
    assert snapshot["user_id"] is None
    assert snapshot["display_name"] is None
    assert snapshot["is_admin"] is False


def test_route_auth_status_consomme_le_snapshot(project_temp_dir: Path) -> None:
    app = create_app(_settings(project_temp_dir))
    seen: list[str] = []

    def snapshot(token: str | None) -> dict:
        seen.append(token or "")
        return {
            "credential_count": 1,
            "password_login": True,
            "user_id": "admin",
            "display_name": "Admin",
            "is_admin": True,
        }

    app.state.auth_store.auth_status_snapshot = snapshot  # type: ignore[method-assign]

    async def exercise() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
            client.cookies.set(SESSION_COOKIE, "session-token")
            response = await client.get("/api/auth/status")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json() == {
            "setup_required": False,
            "setup_token_required": False,
            "setup_token_configured": False,
            "password_login": True,
            "authenticated": True,
            "user": "Admin",
            "is_admin": True,
        }
        assert seen == ["session-token"]

    asyncio.run(exercise())
