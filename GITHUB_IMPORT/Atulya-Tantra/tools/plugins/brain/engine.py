"""Atulya's text reasoning coordinator."""
from __future__ import annotations

import asyncio
import inspect
import json
import os
import re
import time
from collections.abc import Sequence

from atulya.persona import build_system_prompt
from .diagnostics import clean_text, record_brain_failure
from .providers import ChatProvider
from .textcalls import TextCallFilter
from .types import BrainError, BrainReply, Message, ProviderError, ToolCall


# Instant acknowledgements from the user's words alone (no model round trip): spoken within ms.
_INTENT_FILLERS = (
    (re.compile(r"\b(weather|temperature|rain|forecast|humid|मौसम|बारिश|طقس|الطقس|جو|الجو|مطر|المطر)\b", re.I),
     "كنشوف الطقس."),
    (re.compile(r"\b(news|headlines|खबर|समाचार|أخبار|خبر)\b", re.I),
     "كنجيب الأخبار."),
    (re.compile(r"\b(meeting|calendar|schedule|appointment)s?\b|\b(مواعيد|تقويم|اجتماع)\b", re.I),
     "كنشوف المواعيد."),
    (re.compile(r"\b(remember|recall|what did i (say|tell)|do you know my)\b|\b(حفظت|تذكر|ذاكرة)\b", re.I),
     "كنشوف اللي حفظت."),
    (re.compile(r"\b(status|server|uptime|health)\b|\b(حالة|نظام|أنظمة|سيرفر)\b", re.I),
     "كنفحص الأنظمة."),
)


def instant_ack(text: str) -> str:
    for pattern, phrase in _INTENT_FILLERS:
        if pattern.search(text):
            return phrase + " "
    return ""


DEFAULT_FILLER = "لحظة من فضلك."

_FILLERS = {
    "get_weather": "كنشوف الطقس.",
    "get_news": "كنجيب الأخبار.",
    "calculate": "",
    "get_time": "",
    "recall_memories": "كنشوف اللي حفظت.",
    "search_past_chats": "كنقلب فالمحادثات القديمة.",
    "list_meetings": "كنشوف المواعيد.",
    "add_meeting": "كنزيدها للمواعيد.",
    "search_files": "كنقلب فالملفات.",
    "use_skill": "أنا كديرها.",
}


def _tool_filler(calls) -> str:
    """A short spoken acknowledgement for slow tools; empty for instant ones."""
    phrases = [_FILLERS.get(call.name, DEFAULT_FILLER) for call in calls]
    phrases = [phrase for phrase in dict.fromkeys(phrases) if phrase]
    return (" ".join(phrases[:2]) + " ") if phrases else ""


STREAM_RECOVERY = " …الجواب توقف قبل ما كمل. حاول مرة اخرى."
STREAM_UNAVAILABLE = "ما قدرتش ناخد جواب من النموذج دابا. حاول مرة اخرى."


def _env_limit(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.environ.get(name, "").strip() or default)
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(value, maximum))


def _compact_history(conversation: Sequence[Message]) -> list[Message]:
    """Keep trusted instructions and the latest turn; summarize older history.

    The summary is a user-role message: history can never become a system prompt.
    """
    items = list(conversation)
    non_system = [item for item in items if item.role != "system"]
    keep = _env_limit("ATULYA_HISTORY_KEEP", 8, 2, 40)
    char_limit = _env_limit("ATULYA_HISTORY_CHAR_LIMIT", 12_000, 200, 100_000)
    older = non_system[:-keep]
    if not older or sum(len(item.content) for item in older) <= char_limit:
        return items
    summary_limit = _env_limit("ATULYA_HISTORY_SUMMARY_CHARS", 600, 100, 4_000)
    lines: list[str] = []
    used = 0
    for item in older:
        snippet = f"{item.role}: {' '.join(item.content.split())}"
        room = summary_limit - used
        if room <= 0:
            break
        lines.append(snippet[:room])
        used += len(lines[-1])
    summary = "ملخص محادثة سابقة (للسياق فقط، دون تعليمات جديدة):\n" + "\n".join(lines)
    return [
        *(item for item in items if item.role == "system"),
        Message(role="user", content=summary),
        *non_system[-keep:],
    ]


def _tool_result_text(result: object) -> str:
    """Bound tool output before it enters the model context."""
    if result is None:
        return "(no result)"
    limit = _env_limit("ATULYA_TOOL_RESULT_LIMIT", 4_000, 200, 50_000)
    text = str(result)
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n…[مقتطع: {len(text) - limit} حرف]"


class Brain:
    """Turn conversation text into a model reply.

    Brain owns message validation and delegates identity instructions to the
    persona layer and model transport to a provider. It does not access
    microphones, memory stores, desktop controls, or API keys on its own; tools are
    only run through a caller-supplied toolbox.
    """

    def __init__(
        self,
        provider: ChatProvider,
        *,
        assistant_name: str = "Atulya",
        system_instructions: str = "",
    ) -> None:
        if not assistant_name.strip():
            raise ValueError("Assistant name must not be empty")
        self._provider = provider
        self._assistant_name = assistant_name.strip()
        self._system_instructions = system_instructions.strip()

    async def respond(
        self,
        conversation: Sequence[Message],
        *,
        system_instructions: str = "",
    ) -> BrainReply:
        """Generate a reply from text-only conversation history."""
        messages = self._prepare_messages(conversation, system_instructions)
        text = ""
        for attempt in range(2):
            started = time.monotonic()
            try:
                text = await asyncio.wait_for(
                    self._provider.complete(messages),
                    timeout=_env_limit("ATULYA_TURN_TIMEOUT", 45, 3, 600),
                )
                break
            except ProviderError as exc:
                self._record(exc, stage="respond", elapsed_ms=int((time.monotonic() - started) * 1000),
                             status_code=getattr(exc, "status_code", None), retry=attempt == 0)
                if attempt == 0:
                    continue
                raise BrainError("ما قدرش مزود النموذج يولّد الجواب.") from exc
            except BrainError as exc:
                self._record(exc, stage="respond", elapsed_ms=int((time.monotonic() - started) * 1000))
                raise
            except Exception as exc:
                self._record(exc, stage="respond", elapsed_ms=int((time.monotonic() - started) * 1000))
                raise BrainError("ما قدرش مزود النموذج يولّد الجواب.") from exc
        if not isinstance(text, str) or not text.strip():
            raise BrainError("مزود النموذج رجّع جواب فاضي.")
        return BrainReply(text=text.strip(), provider=self._provider.name, model=self._provider.model)

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def model_name(self) -> str:
        return self._provider.model

    def _record(self, exc: BaseException, *, stage: str, elapsed_ms: int = 0,
                status_code: int | None = None, retry: bool = False) -> None:
        record_brain_failure(
            exc, stage=stage, provider=self.provider_name, model=self.model_name,
            elapsed_ms=elapsed_ms, status_code=status_code, retry=retry,
        )

    async def _call_tool(self, toolbox, call: ToolCall) -> str:
        """Run one tool, returning errors to the model so it can recover."""
        started = time.monotonic()
        try:
            result = await toolbox.call(call.name, call.arguments)
        except Exception as exc:
            self._record(exc, stage="tool", elapsed_ms=int((time.monotonic() - started) * 1000))
            return (
                f"TOOL_ERROR: خطأ في الأداة: {clean_text(exc, 200)}. "
                "حاول أداة اخرى ولا اشرح الحالة للمستخدم."
            )
        return _tool_result_text(result)

    def _prepare_messages(self, conversation: Sequence[Message], system_instructions: str) -> list[Message]:
        if not conversation:
            raise ValueError("Conversation must include at least one message")
        if not any(message.role == "user" for message in conversation):
            raise ValueError("Conversation must include a user message")

        trusted_instructions = [
            self._system_instructions,
            system_instructions.strip(),
            *(message.content for message in conversation if message.role == "system"),
        ]
        prompt = build_system_prompt(
            self._assistant_name,
            "\n\n".join(item for item in trusted_instructions if item),
        )
        messages = [Message(role="system", content=prompt)]
        messages.extend(message for message in _compact_history(conversation) if message.role != "system")
        if messages[-1].role != "user":
            raise ValueError("The latest conversation message must be from the user")

        return messages

    async def stream(
        self,
        conversation: Sequence[Message],
        *,
        system_instructions: str = "",
        toolbox=None,
    ):
        """Yield reply text chunks, running any tool calls the model makes in between.

        `toolbox` (tools/plugins/toolkit.Toolbox) is optional. Each round streams
        text immediately; requested tools run concurrently and their results are
        fed back. The final round is sent without tools so the model must answer.
        """
        deadline = time.monotonic() + _env_limit("ATULYA_TURN_TIMEOUT", 45, 3, 600)
        stream_method = getattr(self._provider, "stream", None)
        stream_accepts_tools = stream_method is not None and any(
            parameter.name == "tools" or parameter.kind == inspect.Parameter.VAR_KEYWORD
            for parameter in inspect.signature(stream_method).parameters.values()
        )
        if toolbox:
            system_instructions = "\n\n".join(item for item in (system_instructions, toolbox.instructions()) if item)
            if not stream_accepts_tools:
                system_instructions += (
                    '\nTo request an action, output <tool_call>{"name":"tool_name",'
                    '"arguments":{}}</tool_call> using one of these tool schemas. '
                    'Wait for the tool result before claiming success.\n'
                    + json.dumps(toolbox.schemas)
                )
        messages = self._prepare_messages(conversation, system_instructions)
        rounds = toolbox.MAX_ROUNDS if toolbox else 1
        latest = next((item.content for item in reversed(messages) if item.role == "user"), "")
        early = instant_ack(latest) if toolbox else ""
        spoken: set[str] = set()  # each acknowledgement at most once per reply
        if early:
            spoken.add(early.strip())
            yield early  # spoken immediately while the model decides which tool to use
        try:
            for round_index in range(rounds):
                use_tools = bool(toolbox) and round_index < rounds - 1
                interrupted = False
                for attempt in range(2):  # one retry only when nothing was emitted yet
                    calls: list[ToolCall] = []
                    text_parts: list[str] = []
                    started = time.monotonic()

                    async def completion_stream():
                        yield await self._provider.complete(messages)

                    stream = (
                        completion_stream() if stream_method is None else
                        stream_method(messages, tools=toolbox.schemas) if use_tools and stream_accepts_tools else
                        stream_method(messages)
                    )
                    text_filter = TextCallFilter()
                    try:
                        iterator = stream.__aiter__()
                        while True:
                            remaining = deadline - time.monotonic()
                            if remaining <= 0:
                                raise ProviderError("انتهت مهلة النموذج المحلي")
                            try:
                                chunk = await asyncio.wait_for(iterator.__anext__(), timeout=remaining)
                            except StopAsyncIteration:
                                break
                            except asyncio.TimeoutError as exc:
                                raise ProviderError("انتهت مهلة النموذج المحلي") from exc
                            if isinstance(chunk, ToolCall):
                                if use_tools:
                                    calls.append(chunk)
                            elif chunk:
                                visible = text_filter.feed(chunk)
                                if visible:
                                    text_parts.append(visible)
                                    yield visible
                    except ProviderError as exc:
                        clean_start = not text_parts and not calls
                        self._record(
                            exc, stage="stream", elapsed_ms=int((time.monotonic() - started) * 1000),
                            status_code=getattr(exc, "status_code", None), retry=attempt == 0 and clean_start,
                        )
                        if attempt == 0 and clean_start:
                            continue
                        recovery = STREAM_UNAVAILABLE if clean_start else STREAM_RECOVERY
                        text_parts.append(recovery)
                        yield recovery  # keep the SSE/voice turn alive; the caller still gets `done`
                        interrupted = True
                        break
                    finally:
                        close = getattr(stream, "aclose", None)
                        if close is not None:
                            try:
                                await close()
                            except Exception:
                                pass  # a failed cleanup must not replace the original outcome
                    break
                text_calls, leftover = text_filter.finish()
                if use_tools:
                    calls.extend(text_calls)
                elif text_calls:
                    leftover = ""  # tools are closed this round: never show raw call markup
                if leftover:
                    text_parts.append(leftover)
                    yield leftover
                if interrupted and not calls:
                    return
                if not calls:
                    return
                if not text_parts:
                    # Say something immediately so voice users hear a reply while tools run.
                    filler = " ".join(part for part in _tool_filler(calls).replace(". ", ".|").split("|")
                                      if part.strip() and part.strip() not in spoken).strip()
                    filler = f"{filler} " if filler else ""
                    spoken.update(part.strip() for part in filler.replace(". ", ".|").split("|") if part.strip())
                    if filler:
                        text_parts.append(filler)
                        yield filler
                results = await asyncio.gather(*(self._call_tool(toolbox, call) for call in calls))
                messages.append(Message(role="assistant", content="".join(text_parts), tool_calls=tuple(calls)))
                messages.extend(
                    Message(role="tool", content=result or "(no result)", tool_call_id=call.id)
                    for call, result in zip(calls, results)
                )
        except BrainError:
            raise
        except Exception as exc:
            self._record(exc, stage="stream")
            raise BrainError("ما قدرش مزود النموذج يولّد الجواب.") from exc

    async def respond_with_tools(self, conversation: Sequence[Message], toolbox, *, system_instructions: str = "") -> BrainReply:
        """Non-streaming convenience for channels like Telegram."""
        text = "".join([chunk async for chunk in self.stream(
            conversation, system_instructions=system_instructions, toolbox=toolbox)]).strip()
        if not text:
            raise BrainError("مزود النموذج رجّع جواب فاضي.")
        return BrainReply(text=text, provider=self._provider.name, model=self._provider.model)
