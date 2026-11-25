import asyncio
import json
from types import SimpleNamespace

import pytest

from atulya.maintenance import Maintenance
from atulya.mcp_connections import MCPConnections


def test_protected_files_and_stale_proposals_are_never_overwritten(project_temp_dir):
    root = project_temp_dir / "project"
    path = root / "webui" / "controls.css"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"body {color:white}\r\n")
    manager = Maintenance(root, project_temp_dir / "data", project_temp_dir / "models")
    for name in [".env", "tools/bootstrap.py", "atulya/auth.py", "webui/scene/a.js",
                 "../webui/controls.css", str(path)]:
        with pytest.raises(ValueError):
            manager.read(name)
    proposal = manager.propose("webui/controls.css", "body {color:black}\n", "Improve contrast")
    assert path.read_bytes() == b"body {color:white}\r\n"
    path.write_text("changed by someone else", encoding="utf-8")
    with pytest.raises(ValueError, match="changed since"):
        manager.apply(proposal["id"])
    assert path.read_text() == "changed by someone else"


def test_review_apply_and_rollback_preserve_original_bytes(project_temp_dir):
    root = project_temp_dir / "project"
    path = root / "webui" / "controls.css"
    path.parent.mkdir(parents=True)
    original = b"body {color:white}\r\n"
    path.write_bytes(original)
    manager = Maintenance(root, project_temp_dir / "data", project_temp_dir / "models")
    proposal = manager.propose("webui/controls.css", "body {color:black}\n", "Contrast")
    assert manager.apply(proposal["id"])["state"] == "applied"
    assert path.read_bytes() == b"body {color:black}\n"
    assert manager.apply(proposal["id"], rollback=True)["state"] == "rolled_back"
    assert path.read_bytes() == original


def test_mcp_grants_are_required_and_rechecked_on_every_call(project_temp_dir, monkeypatch):
    calls = []
    class Client:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def list_tools(self):
            return SimpleNamespace(tools=[SimpleNamespace(name="echo", description="Echo", input_schema={"type": "object"})])
        async def call_tool(self, name, arguments):
            calls.append((name, arguments))
            return SimpleNamespace(is_error=False, content=[SimpleNamespace(type="text", text="confirmed")])
    import mcp
    monkeypatch.setattr(mcp, "Client", Client)
    async def exercise():
        manager = MCPConnections(project_temp_dir)
        with pytest.raises(ValueError):
            await manager.add("Bad", "https://user:password@example.org/mcp")
        item = await manager.add("Test", "https://example.org/mcp")
        await manager.discover(item["id"])
        with pytest.raises(ValueError, match="not been granted"):
            await manager.call(item["id"], "echo", {})
        await manager.grant(item["id"], "echo", True)
        assert "confirmed" in await manager.call(item["id"], "echo", {"value": "test"})
        await manager.grant(item["id"], "echo", False)
        with pytest.raises(ValueError):
            await manager.call(item["id"], "echo", {})
        assert len(calls) == 1
        await manager.remove(item["id"])
        assert manager.load() == []
    asyncio.run(exercise())


def _stub_client(monkeypatch, calls=None, clients=None):
    class Client:
        def __init__(self, *args, **kwargs):
            if clients is not None:
                clients.append((args, kwargs))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

        async def list_tools(self):
            return SimpleNamespace(tools=[SimpleNamespace(name="echo", description="Echo", input_schema={"type": "object"})])

        async def call_tool(self, name, arguments):
            if calls is not None:
                calls.append((name, arguments))
            return SimpleNamespace(is_error=False, content=[SimpleNamespace(type="text", text="confirmed")])

    import mcp
    monkeypatch.setattr(mcp, "Client", Client)


def test_loopback_http_mcp_is_allowed_with_test_and_grant(project_temp_dir, monkeypatch):
    calls = []
    _stub_client(monkeypatch, calls=calls)

    async def exercise():
        manager = MCPConnections(project_temp_dir)
        item = await manager.add("Local", "http://127.0.0.1:3001/mcp")
        assert item["enabled"] is False
        assert item["tools"] == []
        await manager.discover(item["id"])
        with pytest.raises(ValueError, match="not been granted"):
            await manager.call(item["id"], "echo", {})
        await manager.grant(item["id"], "echo", True)
        assert "confirmed" in await manager.call(item["id"], "echo", {"value": "test"})
        await manager.grant(item["id"], "echo", False)
        with pytest.raises(ValueError, match="not been granted"):
            await manager.call(item["id"], "echo", {})
        assert len(calls) == 1

    asyncio.run(exercise())


def test_ipv6_loopback_http_mcp_is_allowed(project_temp_dir, monkeypatch):
    _stub_client(monkeypatch)

    async def exercise():
        manager = MCPConnections(project_temp_dir)
        item = await manager.add("Local6", "http://[::1]:3001/mcp")
        assert item["url"] == "http://[::1]:3001/mcp"
        await manager.discover(item["id"])
        await manager.grant(item["id"], "echo", True)
        assert "confirmed" in await manager.call(item["id"], "echo", {})

    asyncio.run(exercise())


@pytest.mark.parametrize("url", [
    "http://localhost:3001/mcp",
    "http://127.0.0.2/mcp",
    "http://127.1/mcp",
    "http://[::ffff:127.0.0.1]/mcp",
    "http://127.0.0.1@evil.example/mcp",
    "http://evil.example/mcp",
    "http://127.0.0.1:3001/mcp?x=1",
    "http://127.0.0.1:3001/mcp#f",
    "http://u:p@127.0.0.1:3001/mcp",
])
def test_loopback_spoofing_is_rejected(project_temp_dir, monkeypatch, url):
    async def exercise():
        manager = MCPConnections(project_temp_dir)
        with pytest.raises(ValueError):
            await manager.add("Bad", url)

    asyncio.run(exercise())


def test_remote_https_rules_are_unchanged(project_temp_dir, monkeypatch):
    _stub_client(monkeypatch)

    async def exercise():
        manager = MCPConnections(project_temp_dir)
        await manager.add("Remote", "https://example.org/mcp")
        for bad in ("https://user:password@example.org/mcp", "https://example.org/mcp?x=1",
                    "http://example.org/mcp"):
            with pytest.raises(ValueError):
                await manager.add("Bad", bad)

    asyncio.run(exercise())


def test_stored_loopback_url_is_revalidated_on_discover_and_call(project_temp_dir, monkeypatch):
    clients = []
    _stub_client(monkeypatch, clients=clients)

    async def exercise():
        manager = MCPConnections(project_temp_dir)
        good = await manager.add("Local", "http://127.0.0.1:3001/mcp")
        manager.path.write_text(json.dumps([{**good, "url": "http://evil.example/mcp"}]), encoding="utf-8")
        with pytest.raises(ValueError):
            await manager.discover(good["id"])
        manager.path.write_text(json.dumps([{**good, "url": "http://evil.example/mcp", "enabled": True,
                                             "tools": [{"name": "echo", "granted": True}]}]), encoding="utf-8")
        with pytest.raises(ValueError):
            await manager.call(good["id"], "echo", {})

    asyncio.run(exercise())
    assert clients == []
