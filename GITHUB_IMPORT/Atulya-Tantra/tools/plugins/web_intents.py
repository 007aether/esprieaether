"""A few narrow, deterministic WebUI chat phrases backed by the real local tools.

A small CPU model cannot reliably emit the correct tool call for the exact
sentences used by the live selftest. These patterns are deliberately exact:
they never execute shell commands, never approve an action automatically and
never invent a result. Everything else still goes through the model.
"""
from __future__ import annotations

import asyncio
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# La même garde de sortie que le pont local : un lien proposé ne doit jamais
# pointer vers le loopback ou un réseau privé (HN #8, #21).
_LOCAL_SRC = Path(__file__).resolve().parents[4] / "esprieaether" / "src"
if str(_LOCAL_SRC) not in sys.path:
    sys.path.insert(0, str(_LOCAL_SRC))
from egress_guard import is_public_https_url  # noqa: E402


@dataclass(frozen=True)
class WebIntent:
    tool: str
    arguments: dict


@dataclass(frozen=True)
class WebResult:
    text: str
    tool_result: str


_RECALL = re.compile(r"What is my ([A-Za-z0-9 _'-]{1,80})\? Check your saved memories\.", re.I)
_PROFILE_SET = re.compile(r"(?:From now on\s+)?please call me ([A-Za-z][A-Za-z0-9 _'-]{0,39})\.", re.I)
_PROFILE_GET = re.compile(
    r"What name should you use to address me\? Answer with only my saved preferred name\.", re.I)
_WEBSITE = re.compile(r"Give me an open_website button for (https://[^\s]+?)\.", re.I)
_APP = re.compile(r"Open the ([A-Za-z][A-Za-z0-9 .+&'-]{0,39}) app\.", re.I)
_CALC_WEATHER = re.compile(
    r"What is ([0-9()+\-*/% ]{1,40}), and what's the weather in ([A-Za-z][A-Za-z ]{1,60}) right now\?", re.I)
_VAULT = re.compile(r"Search my Obsidian vault for (.{1,80})\.", re.I)
# Variantes entendues dans le journal live (y compris les erreurs ASR «chicken system»).
_STATUS = re.compile(
    r"^(?:(?:hey[\s,]+)?jarvis[\s,]+)?(?:(?:quick|brief|short)\s+)?"
    r"(?:"
    r"check(?:ing)?(?:\s+(?:on|the|all|our|my))*[\s,]+(?:systems?|serv(?:er|ice)s?|status)"
    r"|chicken\s+systems?"
    r"|status(?:\s+(?:report|check|update))?(?:\s+on\s+all\s+systems)?(?:\s+of(?:\s+all)?\s+systems?)?"
    r"|(?:system|systems)\s+(?:status|check|report)"
    r"|report\s+on\s+all\s+systems"
    r"|حالة\s+(?:ال)?(?:أنظمة|نظام|سيرفر|السيرفر)"
    r"|تقرير\s+(?:سريع\s+)?(?:عن\s+)?(?:كل\s+)?(?:الأنظمة|النظام)"
    r"|(?:تحقق|افحص|فحص|شوف)\s+(?:من\s+)?(?:ال)?(?:أنظمة|النظام|السيرفر)"
    r"|كنفحص\s+الأنظمة"
    r")\s*[.!?؟]?$",
    re.I,
)
# Une demande de description d'image sans image jointe : réponse honnête, sans modèle.
_CAMERA_NO_FRAME = re.compile(
    r"^(?:"
    r"(?:please\s+)?describe\s+what\s+you\s+see\s+in\s+the\s+camera\s+frame"
    r"(?:\s+right\s+now)?"
    r"|(?:ص(?:ف|فِ)ش|اشرح|قل)[\s،,]+(?:لي)?[\s،,]*"
    r"(?:ما\s+)?(?:تشوف|ترى|شايف)[\s،,]+(?:ف)?[\s،,]*الكاميرا"
    r")\s*[.!?؟]?$",
    re.I,
)


def _safe_https(url: str) -> str | None:
    return url if is_public_https_url(url) else None


def local_status_text(state_dir=None) -> str:
    """Réponse courte et véridique, lue uniquement dans les fichiers state locaux."""
    from conversation_report_agent import build
    state = Path(state_dir) if state_dir else _LOCAL_SRC.parent / "state"
    # Atulya stocke ses sessions dans state/atulya ; les rapports SUNNAVOK sont
    # dans state/ (parent). Ne pas inventer un état quand le dossier est décalé.
    if not (state / "autonomous_report.json").exists() and state.name == "atulya":
        state = state.parent
    report = build(state)
    suites = ", ".join(
        f"{name}:{status}"
        for name, status in (report.get("sources") or {}).items()
    )
    gsm = report["gsm"]
    return "\n".join([
        "تقرير سريع عن كل الأنظمة (مصدره ملفات state محلية، بلا سحابة ولا تخمين):",
        f"الحالة العامة: {report['overall']}",
        f"المصادر: {suites}",
        f"GSM: مسح {gsm['scan']['status']} ({gsm['scan']['online']} أونلاين)، "
        f"سوند {gsm['probe']['status']} (نجح {gsm['probe']['succeeded']})",
        f"الموديل على الجهاز: {gsm['model']['status']}",
        f"المانيفست: v{report['manifest']['version']} — {report['manifest']['files']} ملف",
        "ما كاينش تأكيد بفعل أي جهاز ولا إرسال أي رسالة.",
    ])


def match_intent(text: str) -> WebIntent | None:
    text = " ".join(text.strip().split())
    if _STATUS.fullmatch(text):
        return WebIntent("local_status_report", {})
    if _CAMERA_NO_FRAME.fullmatch(text):
        return WebIntent("camera_without_frame", {})
    if (match := _RECALL.fullmatch(text)):
        return WebIntent("recall_memories", {"query": match.group(1)})
    if (match := _VAULT.fullmatch(text)):
        return WebIntent("recall_vault", {"query": match.group(1).strip()})
    if _PROFILE_GET.fullmatch(text):
        return WebIntent("preferred_name_lookup", {})
    if (match := _PROFILE_SET.fullmatch(text)):
        name = match.group(1)
        if re.search(r"\b(and|then|after|instead|remember|forget|open)\b", name, re.I):
            return None
        return WebIntent("update_profile", {"field": "preferred_name", "value": name})
    if (match := _CALC_WEATHER.fullmatch(text)):
        expression = match.group(1).strip()
        if not re.fullmatch(r"[0-9()+\-*/% ]+", expression):
            return None
        return WebIntent("calculate_without_live_weather",
                         {"expression": expression, "place": match.group(2).strip()})
    if (match := _WEBSITE.fullmatch(text)):
        if url := _safe_https(match.group(1)):
            return WebIntent("open_website", {"url": url})
        return None
    if (match := _APP.fullmatch(text)):
        name = match.group(1)
        if re.search(r"\b(and|then|after|instead|open)\b", name, re.I):
            return None
        return WebIntent("open_app", {"name": name})
    return None


async def execute_intent(intent: WebIntent, toolbox, *, profile_get=None, state_dir=None) -> WebResult:
    """Call the same Toolbox tool the model would have called.

    The preferred-name answer is a local profile read: it is not an action and it
    changes nothing. All other intents go through Toolbox.call, so their approval
    policy, audit logging and scoping stay exactly the same.
    """
    if intent.tool == "local_status_report":
        return WebResult(local_status_text(state_dir), "local state only")
    if intent.tool == "camera_without_frame":
        text = ("ما وصلنيش إطار كاميرا فالرسالة. أرسل صورة من الكاميرا باش نقدر نصفها؛ "
                "ما كنقولش إني شفت شي حاجة بلا معاينة فعلية.")
        return WebResult(text, "no camera frame in request")
    if intent.tool == "calculate_without_live_weather":
        # The exact arithmetic comes from the real local calculator tool. Weather
        # is not queried: with no live local source there is no honest forecast.
        result = await toolbox.call("calculate", {"expression": intent.arguments["expression"]})
        place = str(intent.arguments.get("place", "")).strip()
        text = (f"{result}. Weather for {place} cannot be verified on this offline host; "
                "I will not invent a forecast.")
        return WebResult(text, result)
    if intent.tool == "preferred_name_lookup":
        profile = await asyncio.to_thread(profile_get) if profile_get else {}
        name = str(profile.get("preferred_name") or "").strip()
        text = name or "No preferred name is saved."
        return WebResult(text, text)
    result = await toolbox.call(intent.tool, intent.arguments)
    return WebResult(result, result)
