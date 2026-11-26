#!/usr/bin/env python3
"""وكيل REA محلي: يقرأ الكود ويستخرج أدلة وblueprint بلا تعديل المُحلَّل.

القراءة فقط: لا شبكة، لا subprocess، لا قتل عمليات، لا commit/push/restart،
ولا جدولة. الأدلة مقتّصة ومساراتها نسبية.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
REA_SKILL = BASE_DIR / "skills" / "rea-reconstruction-companion"
DEFAULT_STATE_DIR = BASE_DIR / "state"
BLUEPRINT_DIR = BASE_DIR / "docs" / "rea" / "esprieaether"

MAX_REFERENCE_CHARS = 20000
MAX_VALUE_CHARS = 200
MAX_FILE_CHARS = 200000
MAX_ITEMS_PER_FIELD = 40
MAX_EVIDENCE_ITEMS = 80

ALLOWED_EXTS = (".py", ".mjs")
EXCLUDED_DIRS = frozenset(
    {".venv", "node_modules", ".git", "__pycache__", "state", ".ecc",
     ".pytest_cache", ".tox", "venv", "env", "dist", "build"}
)

ENTRY_RE = re.compile(r"\b(?:def\s+main\s*\(|createServer\s*\(|app\.(?:post|get)\s*\()")
TODO_RE = re.compile(r"\b(?:TODO|FIXME)\b")
ERROR_RE = re.compile(r"\b(?:except|catch|raise|throw)\b[^\n]{0,120}")
SECRET_RE = re.compile(
    r"(?i)\b(?:password|passwd|token|secret|api[_-]?key|authorization)\b"
    r"(?:\s*[:=]\s*[^\s,;)]*)?"
)
WIN_PATH_RE = re.compile(r"[A-Za-z]:[\\/][^\s,;)\"']+|\\\\[^\s,;)\"']+")
POSIX_PATH_RE = re.compile(r"(?<![A-Za-z0-9_])/(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]*")


def _clip(text: object) -> str:
    """نص أحادي السطر مقتّص، بلا فواصل أسطر."""
    value = re.sub(r"\s+", " ", str(text)).strip()
    return value[:MAX_VALUE_CHARS]


def _scrub(text: object) -> str:
    """إزالة المسارات المطلقة والكلمات الحساسة قبل العرض."""
    value = _clip(text)
    value = WIN_PATH_RE.sub("[path]", value)
    value = POSIX_PATH_RE.sub("[path]", value)
    value = SECRET_RE.sub("[redacted]", value)
    return _clip(value)


def _atomic_write(path: Path, text: str) -> None:
    """كتابة ملف tmp في نفس المجلد ثم استبدال ذري."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def load_reference(name: str) -> str:
    """قراءة مرجع من المهارة، برفض أي خروج من مجلد references."""
    if not isinstance(name, str) or not name or name.strip() != name:
        return ""
    if "/" in name or "\\" in name or ".." in name or "\x00" in name:
        return ""
    ref_dir = (REA_SKILL / "references").resolve()
    candidate = (ref_dir / (name + ".md")).resolve()
    if candidate.parent != ref_dir or not candidate.is_file():
        return ""
    try:
        return candidate.read_text(encoding="utf-8", errors="replace")[:MAX_REFERENCE_CHARS]
    except (OSError, ValueError):
        return ""


def analyze(target_dir: object = BASE_DIR) -> dict:
    """فحص ثابت لملفات .py/.mjs مع أدلة مقتّصة ومسارات نسبية فقط."""
    root = Path(target_dir)
    checked_at = datetime.now(timezone.utc).isoformat()
    by_ext = {".py": 0, ".mjs": 0}
    entrypoints: list[str] = []
    todos: list[str] = []
    error_patterns: list[str] = []
    evidence: list[dict] = []
    lengths: list[dict] = []

    def add(field: str, bucket: list[str], source: str, line_no: int, line: str) -> None:
        snippet = _clip(line)
        if len(bucket) < MAX_ITEMS_PER_FIELD:
            bucket.append(f"{source}:{line_no}: {snippet}")
        if len(evidence) < MAX_EVIDENCE_ITEMS:
            evidence.append({"source": source, "field": field, "value": f"{line_no}: {snippet}"})

    if not root.is_dir():
        return {
            "ok": False, "checked_at": checked_at, "files": 0, "by_ext": by_ext,
            "entrypoints": [], "todos": [], "error_patterns": [], "longest": [], "evidence": [],
        }

    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        dirnames[:] = sorted(
            name for name in dirnames if name not in EXCLUDED_DIRS and not name.startswith(".")
        )
        for filename in sorted(filenames):
            ext = Path(filename).suffix.lower()
            if ext not in ALLOWED_EXTS:
                continue
            path = Path(dirpath) / filename
            try:
                source = path.relative_to(root).as_posix()
            except ValueError:
                continue
            by_ext[ext] += 1
            try:
                text = path.read_text(encoding="utf-8", errors="replace")[:MAX_FILE_CHARS]
            except (OSError, ValueError):
                continue
            lines = text.splitlines()
            lengths.append({"source": source, "lines": len(lines)})
            for line_no, line in enumerate(lines, 1):
                if ENTRY_RE.search(line):
                    add("entrypoint", entrypoints, source, line_no, line)
                if TODO_RE.search(line):
                    add("todo", todos, source, line_no, line)
                if ERROR_RE.search(line):
                    add("error_pattern", error_patterns, source, line_no, line)

    longest = sorted(lengths, key=lambda item: (-item["lines"], item["source"]))[:5]
    return {
        "ok": True,
        "checked_at": checked_at,
        "files": sum(by_ext.values()),
        "by_ext": by_ext,
        "entrypoints": entrypoints,
        "todos": todos,
        "error_patterns": error_patterns,
        "longest": longest,
        "evidence": evidence,
    }


def blueprint(report: dict) -> str:
    """ملخص بالدارجة + أدلة منقّاة + 'شنو ناقص'، بلا مسارات ولا أسرار."""
    files = int(report.get("files") or 0)
    entrypoints = report.get("entrypoints") or []
    todos = report.get("todos") or []
    lines = [
        "# مخطط هندسة عكسية — EsprieAether",
        "",
        "## الملخص",
        f"حلّلنا {files} ملفات محلية قراءةً فقط، بلا أي تعديل فالكود المُحلَّل.",
        f"نقاط الدخول: {len(entrypoints)} • TODO/FIXME: {len(todos)}.",
        "",
        "## الأدلة",
    ]
    evidence = report.get("evidence") or []
    if not evidence:
        lines.append("- ما كاينين أدلة كافية فالعينة.")
    for item in evidence[:10]:
        if not isinstance(item, dict):
            continue
        source = _scrub(Path(str(item.get("source") or "")).name)
        field = _scrub(str(item.get("field") or ""))[:40]
        value = _scrub(item.get("value") or "")
        lines.append(f"- `{source}` • {field}: {value}")
    lines += [
        "",
        "## شنو ناقص",
        "- السلوك وقت التشغيل والمدخلات الحقيقية ما تحققوش.",
        "- المسارات الحرجة محتاجة اختبارات قبل أي تطوير.",
        "",
        "## مقترحات التطوير",
        "- توثيق نقاط الدخول وعقودها قبل لمس التنفيذ.",
        "- تحويل TODO/FIXME إلى اختبارات صغيرة قابلة للتحقق.",
        "",
    ]
    return "\n".join(lines)


def run(state_dir: object = DEFAULT_STATE_DIR, target_dir: object = BASE_DIR) -> dict:
    """يكتب blueprint وملف selfcheck، ويرجّع حالة الحملة."""
    report = analyze(target_dir)
    markdown = blueprint(report)
    blueprint_path = BLUEPRINT_DIR / "blueprint.md"
    _atomic_write(blueprint_path, markdown + "\n")

    has_files = bool(report["files"])
    state = {
        "ok": bool(report["ok"]),
        "status": "live_verified" if has_files else "no_data_source",
        "checked_at": report["checked_at"],
        "files": report["files"],
        "entrypoints": report["entrypoints"],
        "blueprintPath": str(blueprint_path),
        "next": (
            "راجع الأدلة واختر مقترحاً واحداً للتحقق قبل التطوير."
            if has_files else "وفّر ملفات .py أو .mjs للفحص."
        ),
    }
    _atomic_write(Path(state_dir) / "rea_selfcheck.json", json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    return state


def doctor() -> dict:
    """فحص صحة محلي بحت للواجهة القديمة: المهارة موجودة والقراءة آمنة."""
    reference = load_reference("safe-changes")
    return {
        "ok": REA_SKILL.is_dir(),
        "skill": REA_SKILL.name,
        "reference": bool(reference),
        "engine": "local_readonly",
    }


def inventory(target: object = BASE_DIR) -> dict:
    """جرد سريع للملفات المحلية، بلا أوامر خارجية."""
    report = analyze(target)
    return {
        "ok": bool(report["ok"]),
        "target": Path(target).name,
        "files": report["files"],
        "by_ext": report["by_ext"],
        "longest": report["longest"],
    }


def investigate(target: object = BASE_DIR) -> dict:
    """واجهة الوكلاء القديمة: تحليل محلي وتخزين ملخّص، بلا شبكة ولا mesh."""
    result = analyze(target)
    if result["ok"]:
        result["result"] = {
            "files": result["files"],
            "entrypoints": result["entrypoints"][:10],
            "todos": result["todos"][:10],
        }
    else:
        result["error"] = "target_not_found"
    return result


def status_report() -> str:
    """ملخّص بالدارجة للواجهة القديمة، بلا Telegram ولا HTTP."""
    health = doctor()
    return (
        "🔬 REA — الهندسة العكسية المحلية\n"
        f"المهارة: {_scrub(health['skill'])} • "
        f"الحالة: {'جاهزة' if health['ok'] else 'ما كاينة'}\n"
        "القراءة فقط: لا شبكة، لا أوامر خارجية، لا تعديل فالكود المُحلَّل."
    )


def main() -> None:
    report = analyze(BASE_DIR)
    print("🔬 ملخص فحص REA المحلي")
    print(f"الملفات: {report['files']} • نقاط الدخول: {len(report['entrypoints'])} • TODO/FIXME: {len(report['todos'])}")
    print(f"الحالة: {'live_verified' if report['files'] else 'no_data_source'}")


__all__ = ["REA_SKILL", "DEFAULT_STATE_DIR", "load_reference", "analyze",
           "blueprint", "run", "doctor", "inventory", "investigate", "status_report"]

if __name__ == "__main__":
    main()
