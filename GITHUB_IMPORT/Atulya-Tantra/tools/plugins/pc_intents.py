"""J171 — commandes PC/Internet en langage naturel (darja + English).

Le petit modèle local ne sait pas émettre de façon fiable une URL de recherche
YouTube ni une commande shell exacte. Ces motifs sont déterministes : ils ne
devinent aucun résultat, ne lisent aucun secret et passent tous par la passerelle
gouvernée ``pc_gateway`` (audit + consentement + lignes rouges).
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus

_LOCAL_SRC = Path(__file__).resolve().parents[4] / "esprieaether" / "src"
if str(_LOCAL_SRC) not in sys.path:
    sys.path.insert(0, str(_LOCAL_SRC))

from pc_gateway import is_public_web_url  # noqa: E402

YOUTUBE_SEARCH = "https://www.youtube.com/results?search_query="
YOUTUBE_HOME = "https://www.youtube.com/"

_CONFIRM = re.compile(
    r"^(أكدت|وافقت|أوافق|approve|confirm|رفضت|deny|reject)\s+(act-[a-z0-9-]+)\s*[.!?؟]?$",
    re.I,
)
_RUN = re.compile(
    r"^(?:دير\s+هادي|دير\s+هادشي|نفّذ|نفذ|شغّل\s+أمر|شغل\s+أمر|run\s+command|run)\s*[:،,]?\s*(.+)$",
    re.I,
)
_MUSIC = re.compile(
    r"^(?:شغّل|شغل|شغلى|شغللي|play)\s+"
    r"(?:موسيقى|موسيقى|music|song|أغنية|اغنية|غنّي|غني)?\s*(.{2,90}?)\s*$",
    re.I,
)
_OPEN_YOUTUBE = re.compile(r"^(?:افتح|فتح|open)\s+(?:يوتيوب|youtube)\s*[.!?؟]?$", re.I)
_OPEN_URL = re.compile(r"^(?:افتح|فتح|open)\s+(https?://\S+)\s*[.!?؟]?$", re.I)
_MUSIC_PREFIX = re.compile(r"^(?:موسيقى|موسيقى|music|song|أغنية|اغنية)\s+", re.I)


@dataclass(frozen=True)
class PcIntent:
    kind: str
    target: str
    summary: str
    mode: str = "ask_each"


def _youtube_query(text: str) -> str:
    value = _MUSIC_PREFIX.sub("", text.strip()).strip(" !!.؟?،,")
    aliases = {
        "راب مغربي": "rap maroc",
        "الراب المغربي": "rap maroc",
        "راب مغربي راديو": "rap maroc radio",
        "موسيقى راب مغربي": "rap maroc",
        "rap marocain": "rap maroc",
        "moroccan rap": "rap maroc",
    }
    return aliases.get(value.lower(), value)


def match_intent(text: str) -> PcIntent | None:
    value = " ".join(str(text or "").strip().split())
    if not value:
        return None
    if match := _CONFIRM.fullmatch(value):
        word = match.group(1).lower()
        decision = "denied" if word.startswith(("رفضت", "deny", "reject")) else "approved_once"
        return PcIntent("decide", match.group(2), f"قرار {decision} للفعل {match.group(2)}",
                        mode=decision)
    if match := _RUN.fullmatch(value):
        command = match.group(1).strip()
        # « بلا سؤال » / « فالجلسة » : le propriétaire choisit le mode.
        mode = "ask_each"
        if command.startswith("بلا سؤال "):
            mode, command = "auto", command[len("بلا سؤال "):].strip()
        elif command.startswith("فالجلسة "):
            mode, command = "session", command[len("فالجلسة "):].strip()
        if not command:
            return None
        return PcIntent("run_command", command, f"تنفيذ الأمر: {command[:80]}", mode)
    if _OPEN_YOUTUBE.fullmatch(value):
        return PcIntent("open_url", YOUTUBE_HOME, "فتح يوتيوب فصفحة جديدة")
    if match := _OPEN_URL.fullmatch(value):
        url = match.group(1)
        if is_public_web_url(url):
            return PcIntent("open_url", url, f"فتح الصفحة: {url[:80]}")
        return None
    if match := _MUSIC.fullmatch(value):
        query = _youtube_query(match.group(1))
        if not query:
            return None
        url = YOUTUBE_SEARCH + quote_plus(query)
        return PcIntent("open_url", url, f"شغّل {query} على يوتيوب: {url[:100]}")
    return None


def execute_intent(intent: PcIntent, gateway) -> dict:
    """Passe par la passerelle gouvernée ; ne prétend jamais un résultat inventé."""
    if intent.kind == "decide":
        try:
            row = gateway.decide(intent.target, intent.mode)
        except ValueError as exc:
            row = {"text": "ما قدرتش أطبّق القرار: " + str(exc), "status": "refused", "id": ""}
    else:
        row = gateway.request(intent.kind, intent.target, mode=intent.mode)
    return {
        "text": row.get("text") or "",
        "status": row.get("status") or "",
        "id": row.get("id") or "",
        "receipt": {"tool": intent.kind, "arguments": {"target": intent.target},
                    "result": row.get("status") or ""},
    }
