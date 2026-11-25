import asyncio
import json
from datetime import datetime, timedelta, timezone

from atulya.implementation import implementation_status, implementation_tool
from tools.plugins.registry import PluginContext
from tools.plugins.toolkit import Toolbox, TOOLS


def test_work_log_keeps_unfinished_and_user_blocked_work_visible():
    data = implementation_status()
    states = {r["id"]: r["status"] for r in data["items"]}
    assert states["google"] == "waiting_for_user" and states["pc"] == "waiting_for_user"
    # L'enregistrement importé est ancien : il ne peut plus être live_verified.
    assert states["server-health"] == "implemented_unverified"
    assert data["fresh"] is False
    assert data["expiresAt"] < datetime.now(timezone.utc).isoformat()
    assert "Only the owner" in asyncio.run(implementation_tool({}, PluginContext("web", None, None, "other")))


def test_live_claims_expire_after_ttl(tmp_path):
    root = tmp_path
    (root / "docs").mkdir()
    path = root / "docs" / "implementation-status.json"
    payload = {
        "updated": "",
        "scope": "test",
        "items": [{"id": "server-health", "title": "test", "status": "live_verified",
                   "evidence": "local", "next": "retest"}],
    }

    def write(days):
        payload["updated"] = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
        path.write_text(json.dumps(payload), encoding="utf-8")
        return implementation_status(root)

    fresh = write(1)
    assert fresh["fresh"] is True
    assert fresh["items"][0]["status"] == "live_verified"
    assert fresh["items"][0]["verifiedAt"].startswith(payload["updated"])
    assert fresh["items"][0]["expiresAt"] > datetime.now(timezone.utc).isoformat()

    stale = write(30)
    assert stale["fresh"] is False
    assert stale["items"][0]["status"] == "implemented_unverified"
    assert stale["items"][0]["expiresAt"] < datetime.now(timezone.utc).isoformat()


def test_unconnected_hardware_is_not_reported_ready(project_temp_dir, monkeypatch):
    from tools.plugins.system import smart_home
    monkeypatch.setenv("ATULYA_DATA_DIR", str(project_temp_dir))
    monkeypatch.setattr(smart_home, "HASS_URL", "")
    monkeypatch.setattr(smart_home, "HASS_TOKEN", "")
    rows = {r["name"]: r for r in Toolbox(TOOLS, PluginContext("web", None, None)).capabilities}
    assert rows["smart_home_control"]["status"] == "needs_connection"
    assert rows["cast_to_tv"]["status"] == "needs_connection"
    # visual_inspect is owner-only, so this session cannot use it at all: never reported as ready.
    assert rows["visual_inspect"]["status"] != "available"
    assert "Owner-only" in rows["visual_inspect"]["next_step"]
