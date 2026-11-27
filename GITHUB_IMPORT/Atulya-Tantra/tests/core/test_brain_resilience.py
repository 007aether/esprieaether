"""J106-J109: journal local, reprise de flux et garde-fous de la boucle d'outils."""
from __future__ import annotations

import asyncio
import json
import sys

from tools.plugins.brain import Brain, Message, ProviderError, ToolCall
from tools.plugins.brain import diagnostics

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _journal(tmp_path, monkeypatch):
    monkeypatch.setenv("ATULYA_DATA_DIR", str(tmp_path))
    return tmp_path / "brain_errors.jsonl"


def _records(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


async def _collect(stream):
    return "".join([chunk async for chunk in stream])


class ScriptedProvider:
    name = "stub"
    model = "dolphin3"

    def __init__(self, script):
        self.script = list(script)
        self.calls: list[list[Message]] = []

    async def stream(self, messages, tools=None):
        self.calls.append(list(messages))
        action = self.script.pop(0) if self.script else ["جاهز."]
        if isinstance(action, Exception):
            raise action
        for item in action:
            if isinstance(item, Exception):
                raise item
            yield item


def test_journal_records_cause_without_secrets(tmp_path, monkeypatch):
    path = _journal(tmp_path, monkeypatch)
    cause = RuntimeError("Bearer sk-abcdefghijklmnopqrstuvwxyz passport 1234")
    exc = ProviderError("فشل api_key=supersecret", status_code=502)
    exc.__cause__ = cause

    diagnostics.record_brain_failure(
        exc, stage="stream", provider="stub", model="dolphin3", elapsed_ms=17, retry=True,
    )

    raw = path.read_text(encoding="utf-8")
    [record] = _records(path)
    assert record["type"] == "ProviderError"
    assert record["cause_type"] == "RuntimeError"
    assert record["status_code"] == 502
    assert record["retry"] is True
    assert "supersecret" not in raw
    assert "passport" not in raw
    assert "<redacted>" in raw


def test_transient_stream_failure_is_retried_once(tmp_path, monkeypatch):
    path = _journal(tmp_path, monkeypatch)
    provider = ScriptedProvider([ProviderError("انقطع التدفق"), ["جاهز."]])
    brain = Brain(provider)

    text = asyncio.run(_collect(brain.stream(
        [Message(role="user", content="هل أنت جاهز؟")])))

    assert text == "جاهز."
    assert len(provider.calls) == 2
    records = _records(path)
    assert len(records) == 1
    assert records[0]["retry"] is True
    assert "انقطع التدفق" in records[0]["message"]


def test_midstream_failure_yields_recovery_without_duplicate_text(tmp_path, monkeypatch):
    path = _journal(tmp_path, monkeypatch)
    provider = ScriptedProvider([["مرحبا", ProviderError("النموذج توقف")]])
    brain = Brain(provider)

    text = asyncio.run(_collect(brain.stream(
        [Message(role="user", content="أهلا")])))

    assert text.count("مرحبا") == 1
    assert "توقف" in text
    assert len(provider.calls) == 1
    [record] = _records(path)
    assert record["retry"] is False


def test_stalled_local_model_is_bounded(tmp_path, monkeypatch):
    path = _journal(tmp_path, monkeypatch)
    monkeypatch.setenv("ATULYA_TURN_TIMEOUT", "3")

    class StalledProvider:
        name = model = "stalled"

        async def stream(self, messages, tools=None):
            yield "كنفحص الأنظمة. "
            await asyncio.sleep(30)
            yield "جاهز."

    text = asyncio.run(_collect(Brain(StalledProvider()).stream(
        [Message(role="user", content="أهلا")])))

    assert "كنفحص الأنظمة." in text
    assert "جاهز." not in text
    assert ("الجواب توقف" in text) or ("ما قدرتش" in text)
    assert _records(path), "l'expiration doit être journalisée"


class FailingToolbox:
    MAX_ROUNDS = 2
    schemas = [{"type": "function", "function": {"name": "bad"}}]

    def instructions(self):
        return ""

    async def call(self, name, arguments):
        raise RuntimeError("boom api_key=toolsecret")


class ToolErrorProvider:
    name = model = "tool-error-test"

    def __init__(self):
        self.calls: list[list[Message]] = []

    async def stream(self, messages, tools=None):
        self.calls.append(list(messages))
        if not any(item.role == "tool" for item in messages):
            yield ToolCall("c1", "bad", "{}")
            return
        result = next(item.content for item in messages if item.role == "tool")
        assert "TOOL_ERROR" in result
        assert "خطأ في الأداة" in result
        assert "toolsecret" not in result
        yield "خلصت."


def test_tool_exceptions_return_to_model_and_are_journaled(tmp_path, monkeypatch):
    path = _journal(tmp_path, monkeypatch)
    provider = ToolErrorProvider()
    text = asyncio.run(_collect(Brain(provider).stream(
        [Message(role="user", content="ديرها")], toolbox=FailingToolbox())))

    assert "خلصت." in text
    assert len(provider.calls) == 2
    records = _records(path)
    assert any(item["stage"] == "tool" for item in records)
    assert "toolsecret" not in path.read_text(encoding="utf-8")


class LongResultToolbox:
    MAX_ROUNDS = 2
    schemas = [{"type": "function", "function": {"name": "long"}}]

    def instructions(self):
        return ""

    async def call(self, name, arguments):
        return "x" * 9000


class LongResultProvider:
    name = model = "long-result-test"

    def __init__(self):
        self.calls: list[list[Message]] = []

    async def stream(self, messages, tools=None):
        self.calls.append(list(messages))
        if not any(item.role == "tool" for item in messages):
            yield ToolCall("c1", "long", "{}")
            return
        result = next(item.content for item in messages if item.role == "tool")
        assert len(result) <= 1200
        assert "مقتطع" in result
        yield "خلصت."


def test_tool_results_are_capped_before_they_reach_the_model(tmp_path, monkeypatch):
    _journal(tmp_path, monkeypatch)
    monkeypatch.setenv("ATULYA_TOOL_RESULT_LIMIT", "1000")
    provider = LongResultProvider()
    text = asyncio.run(_collect(Brain(provider).stream(
        [Message(role="user", content="جيب النتيجة")], toolbox=LongResultToolbox())))

    assert "خلصت." in text
    assert len(provider.calls) == 2


def test_long_history_is_compacted_without_losing_the_last_question(tmp_path, monkeypatch):
    _journal(tmp_path, monkeypatch)
    monkeypatch.setenv("ATULYA_HISTORY_KEEP", "4")
    monkeypatch.setenv("ATULYA_HISTORY_CHAR_LIMIT", "200")
    provider = ScriptedProvider(["جواب."])
    conversation = [
        Message(role="user", content=f"سؤال قديم {index} " + ("ك" * 100))
        for index in range(12)
    ] + [Message(role="user", content="السؤال الأخير")]

    text = asyncio.run(_collect(Brain(provider).stream(conversation)))

    assert text == "جواب."
    first_round = provider.calls[0]
    assert len(first_round) < len(conversation) + 1
    assert any("ملخص محادثة سابقة" in item.content for item in first_round if item.role == "user")
    assert first_round[-1].content == "السؤال الأخير"
