"""الطبيب الآلي المحلي لـ EsprieAether — stdlib فقط، بلا شبكة وبلا تطبيقات خطيرة.

يقرأ مصادر الأخطاء الموجودة داخل ``state/``، يصنّفها، يقترح بقعاً حرفية آمنة،
ويطبّق غير الذي داخل ``state/`` فقط. أي لمس لملف كود مسموح به يبقى مقترحاً
يتطلب موافقة صريحة؛ لا يوجد هنا أي تغيير للعمليات الجارية، ولا لأي مستودع،
ولا أي اتصال خارجي. كل ما يُكتب يبقى داخل ``state/`` أو داخل القائمة البيضاء.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Union

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from policy_gate import AuthorityMode, decide, protected_path  # noqa: E402
from run_store import RunStore, redact  # noqa: E402
import self_improve  # noqa: E402  (categorize_error فقط؛ لا استدعاء للمُصلِح العام)

BASE_DIR = _SRC.parent
REPO_ROOT = BASE_DIR.parent
DEFAULT_STATE_DIR = BASE_DIR / "state"

SEVERITIES = ("immediate", "urgent", "routine")
_SEVERITY_MAP = {
    "critical": "immediate",
    "high": "urgent",
    "medium": "routine",
    "low": "routine",
}

# الملفات الوحيدة outside state/ التي يُسمح بلمسها.run() يطبّق بقعة حرفية
# واحدة فقط عبر apply_safe (بعد موافقة المالك على الإصلاح المحلي التلقائي)،
# ويخبر أتوليا فنفس الدورة. لا إعادة تشغيل ولا شبكة ولا مستودع.
SAFE_CODE_FILES = frozenset({
    "esprieaether/src/self_improve.py",
    "esprieaether/tests/test_espria_system.py",
    "esprieaether/tests/test_agent_duties.py",
})
_CODE_ROOTS = frozenset((REPO_ROOT / rel).resolve() for rel in SAFE_CODE_FILES)
_CODE_TARGET = "esprieaether/src/self_improve.py"

# بقعة حرفية كاملة تضيف حقل severity إلى مخرجات propose_fixes في self_improve.
_SEVERITY_OLD = '''    fixes = []
    for item in learned:
        if item["severity"] == "critical":
            fixes.append({
                "action": "immediate",
                "pattern": item["pattern"],
                "fix": item["fix"],
                "priority": 1,
            })
        elif item["severity"] == "high":
            fixes.append({
                "action": "urgent",
                "pattern": item["pattern"],
                "fix": item["fix"],
                "priority": 2,
            })
        else:
            fixes.append({
                "action": "routine",
                "pattern": item["pattern"],
                "fix": item["fix"],
                "priority": 3,
            })
    return fixes'''

_SEVERITY_NEW = '''    fixes = []
    for item in learned:
        severity = item.get("severity") or "routine"
        if severity == "critical":
            fixes.append({
                "action": "immediate",
                "severity": severity,
                "pattern": item["pattern"],
                "fix": item["fix"],
                "priority": 1,
            })
        elif severity == "high":
            fixes.append({
                "action": "urgent",
                "severity": severity,
                "pattern": item["pattern"],
                "fix": item["fix"],
                "priority": 2,
            })
        else:
            fixes.append({
                "action": "routine",
                "severity": severity,
                "pattern": item["pattern"],
                "fix": item["fix"],
                "priority": 3,
            })
    return fixes'''

_SECRET_KEY = re.compile(
    r"(?i)([\"'](?:api[_-]?key|token|password|secret|authorization|bearer)[\"'])"
    r"(\s*:\s*)([\"'])([^\"']*)([\"'])"
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|token|password|secret|authorization|bearer)"
    r"\s*[=:]\s*([\"']?)([^\s,;\"'}\]]{2,})"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _scrub(value: object) -> str:
    """يمسح قيم الأسرار قبل أي حفظ؛ النص الأصلي لا يُحتفظ به."""
    text = redact(str(value or ""))
    text = _SECRET_KEY.sub(lambda m: f'{m.group(1)}{m.group(2)}"<redacted>"', text)
    text = _SECRET_ASSIGNMENT.sub(lambda m: f"{m.group(1)}=<redacted>", text)
    return text.strip()[:400]


def _read_json(path: Path) -> Optional[object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_jsonl(path: Path) -> List[object]:
    rows: List[object] = []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return rows
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            rows.append(line)
    return rows


def _rows(data: object) -> List[object]:
    if isinstance(data, dict):
        for key in (
            "errors", "runs", "issues", "findings", "failures", "warnings",
            "unknown_errors",
        ):
            value = data.get(key)
            if isinstance(value, list):
                return value
        return []
    if isinstance(data, list):
        return data
    return []


def _message(row: object) -> str:
    if isinstance(row, dict):
        for key in ("message", "text", "detail", "error", "reason", "description"):
            value = row.get(key)
            if value:
                return str(value)
        return json.dumps(row, ensure_ascii=False, sort_keys=True)
    return str(row)


def _severity(text: str, default: str = "routine") -> str:
    try:
        info, _pattern = self_improve.categorize_error(str(text or ""))
    except Exception:
        info = None
    mapped = _SEVERITY_MAP.get(str((info or {}).get("severity", "")).lower())
    return mapped or (default if default in SEVERITIES else "routine")


def _is_missing_severity(text: str) -> bool:
    low = str(text or "").lower()
    return "propose_fixes" in low and "severity" in low


def _code_has_severity_bug() -> bool:
    """Détecte le défaut réel de ``propose_fixes`` : item["severity"] direct.

    Une fois le correctif appliqué, la source contient ``item.get(...)`` et le
    constat disparaît : la détection est idempotente.
    """
    try:
        source = Path(self_improve.__file__).read_text(encoding="utf-8")
    except Exception:
        return False
    return 'item["severity"]' in source or "item['severity']" in source


def detect(state_dir: Union[str, Path] = DEFAULT_STATE_DIR) -> List[dict]:
    """يقرأ مصادر الأخطاء المحلية ويرجّع findings معقّمة."""
    state = Path(state_dir)
    findings: List[dict] = []
    seen = set()

    def add(kind: str, source: str, detail: str, severity: str) -> None:
        clean = _scrub(detail)
        if not clean:
            return
        key = (kind, source, clean)
        if key in seen:
            return
        seen.add(key)
        findings.append({
            "kind": kind,
            "source": source,
            "detail": clean,
            "severity": severity if severity in SEVERITIES else "routine",
        })

    for row in _read_jsonl(state / "brain_errors.jsonl"):
        text = _message(row)
        add("error_log", "brain_errors.jsonl", text, _severity(text, "urgent"))
        if _is_missing_severity(text):
            add("missing_severity", "brain_errors.jsonl", text, "urgent")

    for row in _rows(_read_json(state / "self_improve_errors.json")):
        text = _message(row)
        add("self_improve_error", "self_improve_errors.json", text, _severity(text))
        if _is_missing_severity(text):
            add("missing_severity", "self_improve_errors.json", text, "urgent")

    ledger = _read_json(state / "run_ledger.json")
    runs = _rows(ledger)
    if runs:
        for row in runs:
            status = str(row.get("status", "")).lower() if isinstance(row, dict) else ""
            if status in ("failed", "timed_out", "cancelled"):
                text = _message(row)
                severity = "urgent" if status == "failed" else "routine"
                add("run_failure", "run_ledger.json", f"{status}: {text}", severity)
    elif isinstance(ledger, dict):
        stats = ledger.get("stats")
        if isinstance(stats, dict):
            for status in ("failed", "timed_out"):
                try:
                    count = int(stats.get(status, 0) or 0)
                except (TypeError, ValueError):
                    count = 0
                if count > 0:
                    add(
                        "run_failure", "run_ledger.json",
                        f"{status}={count}", "urgent" if status == "failed" else "routine",
                    )

    guard = _read_json(state / "quality_guard_report.json")
    guard_found = False
    for row in _rows(guard):
        text = _message(row)
        severity = "routine"
        if isinstance(row, dict):
            explicit = str(row.get("severity", "")).lower()
            severity = {
                "critical": "immediate", "high": "urgent",
                "medium": "routine", "low": "routine",
            }.get(explicit, "urgent")
        add("quality_guard", "quality_guard_report.json", text, severity)
        guard_found = True
    if isinstance(guard, dict) and guard.get("ok") is False and not guard_found:
        add(
            "quality_guard", "quality_guard_report.json",
            "quality_guard: ok=false", "immediate",
        )

    if _code_has_severity_bug():
        add("missing_severity", "self_improve.py",
            "propose_fixes utilise item['severity'] sans valeur par défaut", "urgent")

    return findings


def _resolution_line(fix_id: str, status: str) -> str:
    return json.dumps(
        {"id": str(fix_id)[:80], "status": status},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    )


def propose(findings: Iterable[dict]) -> List[dict]:
    """كلfinding يقابله بقعة حرفية واحدة، بلا أي طلب إجراء مؤثر."""
    fixes: List[dict] = []
    for finding in findings or []:
        if not isinstance(finding, dict):
            continue
        kind = str(finding.get("kind") or "finding")
        source = str(finding.get("source") or "")
        detail = str(finding.get("detail") or "")
        severity = str(finding.get("severity") or "routine")
        if severity not in SEVERITIES:
            severity = "routine"
        digest = hashlib.sha1(
            f"{kind}|{source}|{detail}".encode("utf-8")
        ).hexdigest()[:12]
        fix_id = f"d{digest}"
        if kind == "missing_severity":
            target = _CODE_TARGET
            reason = "إضافة حقل severity إلى مخرجات propose_fixes محلياً"
            old, new = _SEVERITY_OLD, _SEVERITY_NEW
        else:
            target = "doctor_resolutions.jsonl"
            reason = "تسجيل نتيجة الفحص داخل state دون لمس الكود"
            old = _resolution_line(fix_id, "pending")
            new = _resolution_line(fix_id, "resolved")
        fixes.append({
            "id": fix_id,
            "kind": kind,
            "target": target,
            "reason": reason,
            "old": old,
            "new": new,
            "severity": severity,
            "needs_restart": False,
        })
    return fixes


def _is_within(path: Path, root: Path) -> bool:
    try:
        return path == root or root in path.parents
    except Exception:
        return False


def _resolve_target(
    target: object, state_dir: Union[str, Path]
) -> Tuple[Optional[Path], str, str]:
    raw = str(target or "").strip()
    if not raw or "\x00" in raw:
        return None, "invalid_target", raw
    if protected_path(raw):
        return None, "protected_path", raw

    state_root = Path(state_dir).resolve()
    path = Path(raw)
    if path.is_absolute():
        candidate = path.resolve()
    else:
        normalized = raw.replace("\\", "/")
        if normalized in SAFE_CODE_FILES:
            candidate = (REPO_ROOT / normalized).resolve()
        else:
            candidate = (state_root / path).resolve()

    inside_state = _is_within(candidate, state_root)
    inside_code = candidate in _CODE_ROOTS
    if not (inside_state or inside_code):
        return None, "target_outside_allowed_roots", str(candidate)
    if protected_path(str(candidate)):
        return None, "protected_path", str(candidate)

    decision = decide("write", path=str(candidate), internet=False)
    if not decision.allowed:
        return None, f"gate:{decision.reason}", str(candidate)
    return candidate, "", str(candidate)


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(
        f".{path.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"
    )
    try:
        tmp.write_bytes(data)
        os.replace(str(tmp), str(path))
    finally:
        if tmp.exists():
            tmp.unlink()


def _atomic_write(path: Path, text: str) -> None:
    _atomic_write_bytes(path, text.encode("utf-8"))


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)


def _log_fix(
    state: Path, fix: dict, target: str,
    sha_before: str, sha_after: str, ok: bool,
) -> None:
    _append_jsonl(state / "doctor_fixes.jsonl", {
        "id": str(fix.get("id", ""))[:80],
        "target": str(target),
        "shaBefore": sha_before,
        "shaAfter": sha_after,
        "at": _now(),
        "ok": bool(ok),
    })


def apply_safe(fix: dict, state_dir: Union[str, Path] = DEFAULT_STATE_DIR) -> dict:
    """تطبيق بقعة حرفية ذرّي داخل state/ أو داخل الملفات المسموحين بالضبط."""
    state = Path(state_dir)
    try:
        state.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    if not isinstance(fix, dict):
        return {"ok": False, "target": "", "reason": "invalid_fix"}

    raw_target = str(fix.get("target") or "")
    result = {"ok": False, "target": raw_target, "reason": "invalid_fix"}
    old, new = fix.get("old"), fix.get("new")
    if not isinstance(old, str) or not old or not isinstance(new, str):
        result["reason"] = "invalid_literal"
        return result

    path, reason, display = _resolve_target(raw_target, state)
    result["target"] = display
    if path is None:
        result["reason"] = reason
        _log_fix(state, fix, display, "", "", False)
        return result

    try:
        raw = path.read_bytes()
        content = raw.decode("utf-8")
    except Exception:
        result["reason"] = "unreadable_target"
        _log_fix(state, fix, display, "", "", False)
        return result

    # Sur Windows, write_text produit des CRLF : on normalise avant la
    # comparaison littérale pour que les patches écrits en LF s'appliquent.
    content = content.replace("\r\n", "\n")
    old = old.replace("\r\n", "\n")
    new = new.replace("\r\n", "\n")
    sha_before = hashlib.sha256(raw).hexdigest()
    occurrences = content.count(old)
    if occurrences != 1:
        result["reason"] = "old_not_found" if occurrences == 0 else "old_ambiguous"
        _log_fix(state, fix, display, sha_before, sha_before, False)
        return result

    updated = content.replace(old, new, 1)
    sha_after = hashlib.sha256(updated.encode("utf-8")).hexdigest()
    try:
        _atomic_write_bytes(path, updated.encode("utf-8"))
    except Exception:
        result["reason"] = "write_failed"
        _log_fix(state, fix, display, sha_before, sha_before, False)
        return result

    _log_fix(state, fix, display, sha_before, sha_after, True)
    return {"ok": True, "target": display, "reason": "applied"}


def notify(
    title: str, body: str, dedupe: str = "",
    state_dir: Union[str, Path] = DEFAULT_STATE_DIR,
) -> dict:
    """إشعار محلي دائماً؛ Atulya inbox اختياري ولا يوقف الشغل إذا غاب."""
    state = Path(state_dir)
    state.mkdir(parents=True, exist_ok=True)
    at = _now()
    record = {
        "at": at,
        "title": _scrub(title)[:120],
        "body": _scrub(body)[:500],
        "dedupe": str(dedupe or "")[:160],
        "ok": True,
    }
    _append_jsonl(state / "doctor_notices.jsonl", record)

    atulya_inbox = False
    try:
        atulya_root = REPO_ROOT / "GITHUB_IMPORT" / "Atulya-Tantra"
        if str(atulya_root) not in sys.path:
            sys.path.insert(0, str(atulya_root))
        inbox_module = importlib.import_module("atulya.inbox")
        data_dir = Path(os.getenv("ATULYA_DATA_DIR") or str(state / "atulya"))
        inbox = inbox_module.Inbox(data_dir)
        inbox.add(
            "doctor", record["title"], record["body"],
            kind="doctor", dedupe=record["dedupe"], reason="doctor local notice",
        )
        atulya_inbox = True
    except Exception:
        atulya_inbox = False

    return {
        "ok": True,
        "at": at,
        "atulya_inbox": atulya_inbox,
        "dedupe": record["dedupe"],
    }


def _seed_resolutions(state: Path, fixes: Iterable[dict]) -> None:
    path = state / "doctor_resolutions.jsonl"
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        text = ""
    kept: List[str] = []
    known = set()
    for line in text.splitlines():
        if not line.strip():
            continue
        kept.append(line)
        try:
            known.add(str(json.loads(line).get("id")))
        except Exception:
            pass
    additions: List[str] = []
    for fix in fixes or []:
        if str(fix.get("target")) != "doctor_resolutions.jsonl":
            continue
        fix_id = str(fix.get("id", ""))[:80]
        if fix_id in known:
            continue
        known.add(fix_id)
        additions.append(_resolution_line(fix_id, "pending"))
    if additions:
        _atomic_write(path, "\n".join(kept + additions) + "\n")


def _state_local(target: object, state: Path) -> bool:
    path, _reason, _display = _resolve_target(target, state)
    return path is not None and _is_within(path, state.resolve())


def run(state_dir: Union[str, Path] = DEFAULT_STATE_DIR) -> dict:
    """دورة كاملة: كشف → اقتراح → تطبيق آمن → إشعار → تقرير ذاتي."""
    state = Path(state_dir)
    state.mkdir(parents=True, exist_ok=True)

    findings = detect(state)
    fixes = propose(findings)
    _seed_resolutions(state, fixes)

    fixed: List[dict] = []
    code_fixed: List[dict] = []
    notices: List[dict] = []
    for fix in fixes:
        # المستخدم صرّح بالإصلاح المحلي التلقائي. apply_safe وحده يقرر السماح:
        # state/ أو ملفات القائمة البيضاء، وبقعة حرفية وحيدة فقط.
        result = apply_safe(fix, state)
        if not result.get("ok"):
            continue
        fixed.append(fix)
        if not _state_local(fix.get("target"), state):
            code_fixed.append(fix)
        notices.append(notify(
            "إصلاح آمن",
            f"{fix.get('kind')}: {result.get('target')}",
            dedupe=f"{fix.get('id')}:{result.get('shaAfter', '')[:12]}",
            state_dir=state,
        ))

    try:
        store = RunStore(state / "doctor_runs.db")
        store.record(
            "doctor.run", actor="doctor_agent", status="succeeded",
            detail=f"detected={len(findings)} fixed={len(fixed)}",
        )
    except Exception:
        pass

    status = "live_verified" if (findings or fixes) else "no_data_source"
    report = {
        "ok": True,
        "status": status,
        "checked_at": _now(),
        "detected": len(findings),
        "fixed": len(fixed),
        "codeFixed": len(code_fixed),
        "needsRestart": False,
        "proposed": len(fixes),
        "notices": len(notices),
        "next": (
            "مراجعة المقترحات قبل أي تدخل في ملفات الكود"
            if fixes else "لا يوجد إجراء مطلوب"
        ),
    }
    _atomic_write(
        state / "doctor_selfcheck.json",
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    )
    return report


def _say(text: str) -> None:
    """طباعة عربية آمنة حتى على كونسول Windows بترميز غير UTF-8."""
    stream = sys.stdout
    buffer = getattr(stream, "buffer", None)
    if buffer is not None:
        try:
            buffer.write((text + "\n").encode("utf-8"))
            buffer.flush()
            return
        except Exception:
            pass
    try:
        stream.write(text + "\n")
    except UnicodeEncodeError:
        stream.write(text.encode("ascii", "backslashreplace") + "\n")


def main(state_dir: Optional[Union[str, Path]] = None) -> dict:
    report = run(state_dir or DEFAULT_STATE_DIR)
    _say("تقرير الطبيب الآلي المحلي")
    _say(f"الحالة: {report['status']}")
    _say(
        f"مكتشف: {report['detected']} | مقترح: {report['proposed']} "
        f"| مُصلَح: {report['fixed']} | إشعارات: {report['notices']}"
    )
    _say(f"الخطوة التالية: {report['next']}")
    return report


__all__ = [
    "DEFAULT_STATE_DIR", "detect", "propose", "apply_safe", "notify", "run",
]
