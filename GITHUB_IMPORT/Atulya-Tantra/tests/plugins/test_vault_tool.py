"""J91 — recherche locale dans le vault Obsidian, sans réseau ni cloud."""
import asyncio

from tools.plugins.toolkit import TOOLS_BY_NAME
from tools.plugins.web_intents import match_intent


def test_intent_vault():
    intent = match_intent("Search my Obsidian vault for vision mmproj.")
    assert intent is not None
    assert intent.tool == "recall_vault"
    assert intent.arguments == {"query": "vision mmproj"}


def test_recall_vault_tool_is_local(monkeypatch, tmp_path):
    (tmp_path / "vision.md").write_text(
        "# Vision\nLe mmproj Qwen sert à l'inférence locale.\n", encoding="utf-8")
    monkeypatch.setenv("ESPRIEATHER_VAULT_DIR", str(tmp_path))
    tool = TOOLS_BY_NAME["recall_vault"]
    result = asyncio.run(tool.handler({"query": "vision mmproj"}, None))
    assert "vision.md" in result
    assert "mmproj" in result
