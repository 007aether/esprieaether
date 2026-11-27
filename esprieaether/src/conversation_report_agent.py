#!/usr/bin/env python3
"""J141 — وكيل محلي: تقرير شامل من state + رسالة Atulya + مقترحات معلّقة.

لا شبكة، لا سحابة، لا مفاتيح، لا تنفيذ تلقائي. المقترحات كتبقى ``proposed``
حتى المالك يوافق عليها من HUD. الرسائل كتكتب فأرشيف المحادثة المحلي ديال
Atulya عبر ``ConversationHistory.append`` (دور ``assistant``).
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

BASE_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BASE_DIR.parent
DEFAULT_STATE_DIR = BASE_DIR / "state"
DEFAULT_ATULYA_DIR = BASE_DIR / "state" / "atulya"
CONVERSATION_ID = "wakil_reports"
USER_ID = "admin"
LEDGER = "conversation_report_agent.json"
INTERVAL_HOURS = 24
MAX_MESSAGE_CHARS = 19_000
TTL = timedelta(days=7)
ALLOWED = ("live_verified", "implemented_unverified", "not_available", "needs_user_data")

SOURCES = {
    "bot": "autonomous_report.json",
    "agents": "daily_orchestrator_report.json",
    "gsm_scan": "gsm_status.json",
    "gsm_probe": "gsm_workers.json",
    "model_trial": "gsm_model_trial.json",
    "brain": "brain_metrics.json",
    "brain_proof": "local_brain_verification.json",
    "quality": "quality_guard_report.json",
    "vault": "vault_guard_report.json",
    "backlog": "backlog_scout_report.json",
    "voice": "voice_status.json",
    "github": "github_scout_report.json",
    "doctor": "doctor_selfcheck.json",
    "rea": "rea_selfcheck.json",
    "learning": "learning_selfcheck.json",
    "chat_auth": "chat_auth_selfcheck.json",
    "egress": "egress_selfcheck.json",
}

_STAMP_KEYS = ("checkedAt", "checked_at", "generatedAt", "verifiedAt", "updatedAt", "updated")
_SECRET = __import__("re").compile(
    r"(?i)\b(api[_-]?key|token|password|secret|authorization|bearer)\s*[=:]\s*[^\s,;\"'}\]]{2,}"
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read(path: Path) -> Optional[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def normalize_status(value: object) -> str:
    """Jamais inventer un état : les valeurs inconnues deviennent not_available."""
    return value if isinstance(value, str) and value in ALLOWED else "not_available"


def _fresh(data: Optional[dict], now: datetime) -> bool:
    if not data:
        return False
    for key in _STAMP_KEYS:
        raw = data.get(key)
        if not isinstance(raw, str):
            continue
        try:
            moment = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return timedelta(0) <= now - moment <= TTL
    return True


def _status(data: Optional[dict], now: datetime, key: str = "status") -> str:
    if data is None:
        return "needs_user_data"
    value = data.get(key, data.get("overall"))
    status = normalize_status(value)
    if status == "live_verified" and not _fresh(data, now):
        return "implemented_unverified"
    return status


def build(state_dir=DEFAULT_STATE_DIR, *, now: Optional[datetime] = None) -> dict:
    """Lit uniquement une whitelist de fichiers locaux et rend un rapport honnête."""
    state = Path(state_dir)
    moment = now or _utcnow()
    sources = {key: _read(state / name) for key, name in SOURCES.items()}
    manifest = _read(state / "manifest.json") or _read(ROOT_DIR / "manifest.json") or {}
    bot = sources["bot"] or {}
    scan = sources["gsm_scan"] or {}
    probe = sources["gsm_probe"] or {}
    trial = sources["model_trial"] or {}
    overall = normalize_status(bot.get("overall"))
    gsm = {
        # الإلغاء صريح في ملفات state؛ ما نعيدش اقتراح ربط GSM بعد قرار المالك.
        "cancelled": any(
            bool((sources[key] or {}).get("cancelled"))
            for key in ("gsm_scan", "gsm_probe", "model_trial")
        ),
        "scan": {
            "status": _status(sources["gsm_scan"], moment),
            "online": scan.get("online", 0),
            "adbStates": scan.get("adbStates", {}),
            "adbPort": scan.get("adbPort", "5038"),
        },
        "probe": {
            "status": _status(sources["gsm_probe"], moment),
            "online": probe.get("online", 0),
            "succeeded": probe.get("succeeded", 0),
        },
        "model": {
            "status": _status(sources["model_trial"], moment),
            "reason": str(trial.get("reason") or ""),
        },
    }
    rows = [
        ("الحالة العامة", overall),
        ("Node/Python/Atulya", ", ".join(
            f"{s.get('name', '?')}:{normalize_status(s.get('status'))}"
            for s in bot.get("suites", []) if isinstance(s, dict)
        ) or "not_available"),
        ("الصيانة (git/reload)", "/".join(
            normalize_status((bot.get("maintenance") or {}).get(k))
            for k in ("git", "reload")
        )),
        ("المسح GSM", f"{gsm['scan']['status']} — أونلاين {gsm['scan']['online']}، "
                      f"ADBStates {json.dumps(gsm['scan']['adbStates'], ensure_ascii=False)}"),
        ("سوند endpoints", f"{gsm['probe']['status']} — نجح {gsm['probe']['succeeded']}/"
                           f"{gsm['probe']['online']}"),
        ("موديل على الجهاز", gsm["model"]["status"] + (
            f" — {gsm['model']['reason']}" if gsm["model"]["reason"] else "")),
        ("المانيفست", f"v{manifest.get('version', '?')} — {_manifest_count(manifest)} ملف"),
    ]
    for key, label in (("agents", "الوكلاء اليوميون"), ("brain", "الدماغ المحلي"),
                       ("brain_proof", "إثبات الدماغ"), ("quality", "جودة"),
                       ("vault", "الخزنة"), ("backlog", "قائمة المهام"),
                       ("voice", "الصوت"), ("github", "استطلاع غيت هاب"),
                       ("doctor", "الطبيب"), ("rea", "الهندسة العكسية"),
                       ("learning", "التعلّم"), ("chat_auth", "دخول المحادثة"),
                       ("egress", "المنافذ")):
        rows.append((label, _status(sources[key], moment)))
    lines = [
        f"# تقرير الوكيل الشامل — {_stamp(moment)}",
        "كل الأرقام مصدرها ملفات state محلية. ما كاينش سحابة، تحميل، ولا سر.",
        "الحالات مسموحة غير: " + " | ".join(ALLOWED) + ".",
        "",
        "## الخلاصة",
    ]
    lines.extend(f"- {label}: {value}" for label, value in rows)
    suggestions = make_suggestions(bot, gsm, manifest)
    lines.extend(["", "## مقترحات كتطلب موافقتك (proposed — ما تّنفذش)", ""])
    lines.extend(f"- {item['action']}: {item['reason']}" for item in suggestions)
    lines.extend([
        "",
        "المقترحات كيبقاو فحالة proposed فـ HUD حتى تختار وافق أو ارفض.",
        "التقرير كيتكتب مرة كل 24 ساعة؛ الرسالة فـ محادثة `wakil_reports`.",
    ])
    text = _scrub("\n".join(lines))
    return {
        "checkedAt": _stamp(moment),
        "overall": overall,
        "sources": {key: _status(value, moment) for key, value in sources.items()},
        "gsm": gsm,
        "manifest": {"version": manifest.get("version", ""), "files": _manifest_count(manifest)},
        "suggestions": suggestions,
        "text": text,
    }


def _scrub(text: str) -> str:
    return _SECRET.sub("[redacted]", text)


def _manifest_count(manifest: dict) -> int:
    """Le manifest généré stocke ``files`` comme table path -> sha256."""
    files = manifest.get("files") or []
    if isinstance(files, dict):
        return len(files)
    if isinstance(files, list):
        return len(files)
    return 0


def make_suggestions(bot: dict, gsm: dict, manifest: dict) -> List[dict]:
    """اقتراحات عملية، كلها محلية وقابلة للرفض، بدون أي تنفيذ تلقائي."""
    ideas: List[dict] = []
    if not gsm.get("cancelled") and (
        gsm["scan"]["online"] < 20 or gsm["probe"]["status"] != "live_verified"
    ):
        ideas.append({
            "action": "gsm_relink_readonly",
            "target": f"adb:{gsm['scan']['adbPort']}",
            "reason": "ربط 20 S8 بمنفذ ADB المحلي ثم إعادة المسح قراءة فقط.",
        })
    if not gsm.get("cancelled") and gsm["model"]["status"] == "needs_user_data":
        ideas.append({
            "action": "provide_on_device_model_locally",
            "target": "un seul S8",
            "reason": "وفّر binaire arm64 وGGUF <= 600Mo محلياً باش ن اختبر جهاز واحد.",
        })
    if normalize_status((bot.get("maintenance") or {}).get("git")) != "live_verified":
        ideas.append({
            "action": "review_pending_local_commits",
            "target": "git local",
            "reason": "مراجعة ال commit/push المعلّقين بعد جولة لم تكتمل.",
        })
    if not manifest.get("version"):
        ideas.append({
            "action": "regenerate_local_manifest",
            "target": "manifest.json",
            "reason": "إعادة توليد المانيفست المحلي بعد تغيير الملفات.",
        })
    ideas.append({
        "action": "review_wakil_report",
        "target": CONVERSATION_ID,
        "reason": "اقرأ التقرير وقرر أي مقترح يستحق التنفيذ.",
    })
    return ideas[:6]


def split_text(text: str, limit: int = MAX_MESSAGE_CHARS) -> List[str]:
    """Découpe en messages Atulya valides (1 à 20000 caractères)."""
    chunks: List[str] = []
    buffer = ""
    for line in text.splitlines(keepends=True):
        if len(buffer) + len(line) > limit and buffer:
            chunks.append(buffer.rstrip() + "\n")
            buffer = line
        else:
            buffer += line
    if buffer.strip():
        chunks.append(buffer.rstrip() + "\n")
    return chunks or [text[:limit]]


def propose_suggestions(store, suggestions: Iterable[dict], *, source: str = "wakil_report") -> List[dict]:
    """Une seule proposition par action en attente ; aucun passage à executed."""
    existing = {
        (str(row.get("action")), str(row.get("source")))
        for row in store._load() if row.get("status") == "proposed"
    }
    added: List[dict] = []
    for item in suggestions:
        action = str(item.get("action") or "").strip()
        if not action or (action, source) in existing:
            continue
        added.append(store.propose(
            action,
            target=str(item.get("target") or ""),
            reason=str(item.get("reason") or ""),
            source=source,
        ))
        existing.add((action, source))
    return added


def _history_class():
    vendor = ROOT_DIR / "GITHUB_IMPORT" / "Atulya-Tantra"
    if str(vendor) not in sys.path:
        sys.path.insert(0, str(vendor))
    from atulya.history import ConversationHistory  # import local, aucun réseau
    return ConversationHistory


def run(state_dir=DEFAULT_STATE_DIR, *, atulya_data_dir=None, now=None,
        force: bool = False, history=None, store=None) -> dict:
    """Écrit le rapport dans Atulya et dépose les propositions, sans rien exécuter."""
    from action_request import ActionRequests

    state = Path(state_dir)
    state.mkdir(parents=True, exist_ok=True)
    moment = now or _utcnow()
    ledger_path = state / LEDGER
    previous = _read(ledger_path) or {}
    if not force and previous.get("checkedAt"):
        try:
            last = datetime.fromisoformat(str(previous["checkedAt"]).replace("Z", "+00:00"))
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if timedelta(0) <= moment - last < timedelta(hours=INTERVAL_HOURS):
                return {
                    "ok": True, "ran": False,
                    "status": normalize_status(previous.get("status")),
                    "messages": 0, "proposals": 0,
                    "next": "Prochain rapport dans 24 h ; aucune action exécutée.",
                }
        except ValueError:
            pass

    report = build(state, now=moment)
    store = store or ActionRequests(
        str(state / "action_requests.json"), str(state / "action_audit.jsonl"))
    proposals = propose_suggestions(store, report["suggestions"])
    target_dir = Path(atulya_data_dir or os.environ.get("ESPRIE_ATULYA_DATA_DIR") or DEFAULT_ATULYA_DIR)
    history = history or _history_class()(target_dir)
    prefix = moment.strftime("%Y%m%dT%H%M%SZ")
    chunks = split_text(report["text"])
    messages = []
    if not previous.get("titled"):
        # Un message d'ouverture explicite donne un titre lisible dans la liste des conversations.
        history.append(
            CONVERSATION_ID, f"wakil-title-{prefix}-{uuid.uuid4().hex[:6]}",
            "user", "تقرير الوكيل — تحديث آلي محلي", user_id=USER_ID,
        )
    for index, chunk in enumerate(chunks, 1):
        message_id = f"rpt-{prefix}-{index}-{uuid.uuid4().hex[:8]}"
        history.append(CONVERSATION_ID, message_id, "assistant", chunk, user_id=USER_ID)
        messages.append(message_id)
    ledger = {
        "ok": True,
        "status": report["overall"],
        "checkedAt": _stamp(moment),
        "conversation": CONVERSATION_ID,
        "titled": True,
        "messages": messages,
        "proposals": [str(item.get("id") or "") for item in proposals],
        "next": "Rapport toutes les 24 h ; les suggestions restent proposed jusqu'à décision du propriétaire.",
    }
    tmp = ledger_path.with_name(f"{ledger_path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, ledger_path)
    return {
        "ok": True, "ran": True, "status": report["overall"],
        "messages": len(messages), "proposals": len(proposals),
        "next": ledger["next"],
    }


def main() -> None:
    result = run(force="--force" in sys.argv[1:])
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
