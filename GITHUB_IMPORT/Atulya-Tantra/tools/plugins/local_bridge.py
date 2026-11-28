"""J174 — réponses courtes déterministes et pont de fichiers local vers OpenCode.

Le petit modèle est lent et peut mal comprendre une consigne en darja. Les
phrases ci-dessous ont une réponse courte, véridique et immédiate (aucun appel
réseau, aucun état inventé). Pour les questions qui demandent une vraie décision,
Atulya écrit une question dans un fichier local ; OpenCode répond dans un autre
fichier. Aucune réponse n'est affirmée avant d'exister dans ce fichier.
"""
from __future__ import annotations

import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_LOCAL_SRC = Path(__file__).resolve().parents[4] / "esprieaether" / "src"
if str(_LOCAL_SRC) not in sys.path:
    sys.path.insert(0, str(_LOCAL_SRC))

from pc_gateway import _scrub  # noqa: E402  — même nettoyage que la passerelle PC

_WHO = re.compile(
    r"^(?:من\s+أنت|من\s+انت|شنو\s+أنت|شنو\s+انت|who\s+are\s+you|introduce\s+yourself"
    r"|إسپريإيثر|اسپرياتر|esprieaether|esprie\s*aether)\s*[.!?؟]?$",
    re.I,
)
_CAN = re.compile(
    r"^(?:شنو\s+تقدر\s+تدير|شنو\s+كاين\s+فهاد\s+النظام|what\s+can\s+you\s+do)\s*[.!?؟]?$",
    re.I,
)
_KNOWLEDGE = re.compile(
    r"^(?:.*\b(?:cheno\s+lma3rifa\s+li\s+3andak|lma3rifa\s+li\s+3andak)\b.*"
    r"|شنو\s+(?:المعرفة|معرفة)\s+(?:اللي\s+)?عندك"
    r"|وشنو\s+كاين\s+فالمعرفة"
    r"|what\s+knowledge\s+do\s+you\s+have)\s*[.!?؟]?$",
    re.I,
)
_OVERVIEW = re.compile(
    r"^(?:(?:beritak\s+tedewi|قبل\s+ما\s+(?:تجاوب|ترد|تكتب))\b.*"
    r"|.*\bcheno\s+kayn\s+f\s+nidam\b.*)\s*[.!?؟]?$",
    re.I | re.S,
)
_ASK = re.compile(
    r"^(?:(?:سول|اسأل|سائل|ask)\s+)?"
    r"(?:أوبن\s*كود|وبن\s*كود|open\s*code|opencode)\s*[:،,]?\s*(.{3,500}?)\s*[.!?؟]?$",
    re.I,
)
_BARE_OPENCODE = re.compile(
    r"^(?:أوبن\s*كود|وبن\s*كود|open\s*code|opencode)\s*[.!?؟]?$",
    re.I,
)
_READ = re.compile(
    r"^(?:(?:شنو\s+(?:قال|جاوب)|واش\s+جاوب|ردّ|رد|جواب)\s+(?:أوبن\s*كود|وبن\s*كود|open\s*code|opencode)"
    r"|cheno\s+kantawro)\s*[.!?؟]?$",
    re.I,
)

_WHO_TEXT = (
    "أنا أتوليا، مساعدك المحلي فهاد الجهاز، واللي كتسمّيه Esprieaether أنا بعيني. "
    "كنجاوبك بالدارجة بحروف عربية، "
    "وما كنقولش إن فعل تّدار بلا دليل من ملف ولا نتيجة أداة."
)
_CAN_TEXT = (
    "فهاد الجهاز كاين محادثة وصوت محلي، فتح يوتيوب وصفحات ويب، وأفعال PC محكومة بالموافقة. "
    "ما كنرسلش SMS ولا كنلمس GSM بلا طلب صريح وتأكيد فكل مرة."
)
_KNOWLEDGE_TEXT = (
    "المعرفة المحلية اللي عندي: كاتالوج مؤرّخ لـ50 مستودع AI وتطوير من GitHub، "
    "جسر أسئلة وأجوبة مع OpenCode فـstate/opencode_bridge، "
    "دليل صوت موقّع منك، وبوابة أفعال PC/إنترنت محكومة. "
    "كنجاوب من هاد الملفات المحلية، بلا سحابة ومفاتيح، "
    "وما كنأكدش إن حاجة باقية شغّالة بلا دليل حي."
)
_NO_ANSWER = (
    "ما جاتنيش أي إجابة من OpenCode دابا. سجّل سؤالك فالملف المحلي "
    "وقول «سول أوبن كود: …» باش نزيدو، ولا جرب من بعد."
)


@dataclass(frozen=True)
class BridgeIntent:
    kind: str
    target: str


def bridge_dir(state_dir=None) -> Path:
    """Dossier partagé, toujours hors du dépôt (state/ est en gitignore)."""
    if state_dir is not None:
        return Path(state_dir)
    override = os.environ.get("ATULYA_OPENCODE_BRIDGE_DIR", "").strip()
    return Path(override) if override else _LOCAL_SRC.parent / "state" / "opencode_bridge"


def match_intent(text: str) -> BridgeIntent | None:
    value = " ".join(str(text or "").strip().split())
    if not value:
        return None
    if _OVERVIEW.fullmatch(value):
        return BridgeIntent("overview", "")
    if _KNOWLEDGE.fullmatch(value):
        return BridgeIntent("knowledge", "")
    if _WHO.fullmatch(value) or _CAN.fullmatch(value):
        return BridgeIntent("who" if _WHO.fullmatch(value) else "capabilities", "")
    if _BARE_OPENCODE.fullmatch(value):
        return BridgeIntent("hint", "")
    if match := _ASK.fullmatch(value):
        return BridgeIntent("ask", _scrub(match.group(1)).strip())
    if _READ.fullmatch(value):
        return BridgeIntent("read", "")
    return None


def _write_question(folder: Path, question: str) -> str:
    folder.mkdir(parents=True, exist_ok=True)
    question_id = "q-" + uuid.uuid4().hex[:8]
    row = {
        "kind": "question",
        "id": question_id,
        "text": _scrub(question)[:500],
        "status": "pending",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    with (folder / "questions.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return question_id


def _latest_answer(folder: Path) -> str:
    path = folder / "answers.jsonl"
    if not path.is_file():
        return ""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    found = ""
    for line in lines:
        try:
            row = json.loads(line)
        except (ValueError, TypeError):
            continue
        if row.get("kind") != "answer":
            continue
        text = str(row.get("text") or "").strip()
        if text:
            found = _scrub(text)[:800]
    return found


def execute_intent(intent: BridgeIntent, state_dir=None) -> str:
    """Texte court et véridique, sans jamais simuler une réponse d'OpenCode."""
    if intent.kind == "who":
        return _WHO_TEXT
    if intent.kind == "capabilities":
        return _CAN_TEXT
    if intent.kind == "knowledge":
        return _KNOWLEDGE_TEXT
    if intent.kind == "hint":
        return ("ما كاين سؤال واضح معا «أوبن كود». قول «سول أوبن كود: …» باش نسجّلو، "
                "ولا «شنو قال أوبن كود» باش نقرا الجواب المسجّل.")
    folder = bridge_dir(state_dir)
    if intent.kind == "overview":
        answer = _latest_answer(folder)
        return (
            "بلا تكهّن: أنا أتوليا، واللي كتسمّيه Esprieaether أنا بعيني. "
            "فالنظام كاين محادثة وصوت محلي، بوابة أفعال محكومة، جسر أوبن كود، "
            "وكاتالوج مؤرّخ لـ50 مشروع AI وتطوير. "
            "آخر جواب مسجّل من أوبن كود فالملف المحلي: " + (answer or "ما كاينش جواب مسجّل دابا.")
        )
    if intent.kind == "ask":
        question_id = _write_question(folder, intent.target)
        return (f"سجّلت سؤالك ({question_id}) فالملف المحلي. "
                "قول «شنو قال أوبن كود» باش تشوف الجواب إلا كتبو.")
    if intent.kind == "read":
        answer = _latest_answer(folder)
        return answer if answer else _NO_ANSWER
    return _NO_ANSWER
