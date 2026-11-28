"""J184 — معرفة محلية بمحرك openset-llm، بلا شبكة وبلا ادّعاء حالة حية.

المعلومات من ملف JSON محلي مخزّن بعد قراءة GitHub وREADME/install.sh.
الإجابات حتمية (بلا نموذج) وتقول بوضوح إن الموديل ما تثبّتش عندنا.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_LOCAL_SRC = Path(__file__).resolve().parents[4] / "esprieaether" / "src"
if str(_LOCAL_SRC) not in sys.path:
    sys.path.insert(0, str(_LOCAL_SRC))

from pc_gateway import _scrub  # noqa: E402

_META = Path(__file__).with_name("openset_llm.json")
_ENGINE = r"openset[-\s]*llm"
_WHAT = re.compile(rf"^(?:شنو\s+هو|ما\s+هو|what\s+is)\s+{_ENGINE}\s*[.!?؟]?$", re.I)
_HOW = re.compile(rf"^(?:كيفاش|كيف|how)\s+(?:نستعمل|نشغّل|كيخدم|to\s+run|run)\s+{_ENGINE}\s*[.!?؟]?$", re.I)


@dataclass(frozen=True)
class OpenSetIntent:
    kind: str


def match_intent(text: str) -> OpenSetIntent | None:
    value = " ".join(str(text or "").strip().split())
    if not value:
        return None
    if _WHAT.fullmatch(value):
        return OpenSetIntent("what")
    if _HOW.fullmatch(value):
        return OpenSetIntent("how")
    return None


def _read() -> dict:
    return json.loads(_META.read_text(encoding="utf-8"))


def execute_intent(intent: OpenSetIntent) -> str:
    """نصّ صادق من الملف المحلي غير، ما كيقولش إن المحرك شغّال دابا."""
    try:
        data = _read()
    except (OSError, ValueError, json.JSONDecodeError):
        return "ما عنديش معلومات محلية مؤكدة على openset-llm دابا."
    repo = _scrub(str(data.get("repo") or "opensetlabs/openset-llm"))
    url = _scrub(str(data.get("url") or ""))
    note = _scrub(str(data.get("note") or ""))
    if intent.kind == "what":
        summary = _scrub(str(data.get("summary") or "")) or "-"
        return (
            f"{repo}: {summary}\n"
            f"الرخصة: {_scrub(str(data.get('license') or '-'))} | الإصدار: "
            f"{_scrub(str(data.get('release') or '-'))}\n"
            f"الرابط: {url}\n"
            f"ملاحظة: {note}"
        )
    if intent.kind == "how":
        endpoint = data.get("endpointProposal") or {}
        base = _scrub(str(endpoint.get("baseUrl") or "http://127.0.0.1:8080/v1"))
        model = _scrub(str(endpoint.get("model") or "openset-llm"))
        claims = data.get("claimsFromRepo") or []
        requirements = "؛ ".join(_scrub(str(item)) for item in claims[:3]) or "-"
        return (
            "الطريقة المقترحة (مازال ما فعّلتها): "
            "Linux/WSL2 → clone → install.sh → serve، والـAPI يولي فـ" + base + " بـmodel=" + model + ".\n"
            "المتطلبات من التوثيق: " + requirements + ".\n"
            "ما نزّلتش الموديل ولا بدّلت إعدادات النموذج الحي؛ " + note
        )
    return note or "ما فهمتش السؤال على openset-llm."
