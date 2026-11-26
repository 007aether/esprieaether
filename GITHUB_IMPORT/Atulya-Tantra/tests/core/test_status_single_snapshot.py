"""J140 — /api/status ne collecte les métriques hôte qu'une seule fois."""
from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

from atulya.server import create_app
from atulya.settings import Settings
from conftest import authenticate_test_admin

HOST = {
    "cpu_percent": 12.5,
    "cpu_count": 8,
    "memory_percent": 40.0,
    "memory_used_gb": 4.0,
    "memory_total_gb": 16.0,
    "disk_percent": 25.0,
    "net_up_kbps": 3.0,
    "net_down_kbps": 7.0,
    "uptime_hours": 5.0,
    "battery_percent": None,
    "on_power": None,
}


def test_api_status_utilise_un_seul_snapshot(project_temp_dir: Path, monkeypatch) -> None:
    import atulya.server as server

    calls: list[str] = []

    def fake_snapshot(data_path: str = ".") -> dict:
        calls.append(data_path)
        return dict(HOST)

    monkeypatch.setattr(server.sysmon, "snapshot", fake_snapshot)
    settings = Settings(
        assistant_name="Atulya", host="127.0.0.1", port=8501,
        data_dir=project_temp_dir / "data", models_dir=project_temp_dir / "models",
        model_provider="", model_name="", model_base_url="", model_api_key="",
    )
    app = create_app(settings)

    async def exercise() -> dict:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
            authenticate_test_admin(client, app)
            response = await client.get("/api/status")
            assert response.status_code == 200
            return response.json()

    status = asyncio.run(exercise())
    assert len(calls) == 1
    assert status["system"] == {
        "cpu_percent": 12.5,
        "memory_percent": 40.0,
        "memory_used_gb": 4.0,
        "memory_total_gb": 16.0,
        "disk_percent": 25.0,
    }
    assert status["cpu"]["label"] == "12% · 8 cores"
    assert status["memory"]["label"] == "4.0 / 16.0 GB"
