"""Secret-free JSONL journal for reasoning failures.

Only an allowlist of scalar fields is written. Free text is redacted and capped;
conversation content, prompts, headers and raw exceptions are never persisted.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from atulya.logging_setup import redact
from atulya.settings import PROJECT_ROOT

_JOURNAL = "brain_errors.jsonl"
_MAX_BYTES = 1024 * 1024
_PII = re.compile(r"(?i)\b(?:passport|api[_-]?key|token|secret|password)\b\s*[:=]?\s*\S*")


def clean_text(value: object, limit: int = 300) -> str:
    """Redact secrets and strip free-text fields down to a safe diagnostic slice."""
    text = _PII.sub("<redacted>", redact(str(value or "")))
    text = " ".join(text.split())
    return text[:limit]


def _journal_path() -> Path:
    raw = os.environ.get("ATULYA_DATA_DIR", "").strip()
    path = Path(raw).expanduser() if raw else PROJECT_ROOT / "data"
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path / _JOURNAL


def record_brain_failure(
    exc: BaseException,
    *,
    stage: str,
    provider: object = "",
    model: object = "",
    elapsed_ms: int = 0,
    status_code: int | None = None,
    retry: bool = False,
) -> dict[str, object]:
    """Append one bounded diagnostic record; never raise from logging."""
    try:
        reported_status = status_code if isinstance(status_code, int) else getattr(exc, "status_code", None)
        record: dict[str, object] = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "type": clean_text(type(exc).__name__, 80),
            "message": clean_text(exc),
            "cause_type": clean_text(type(exc.__cause__ or exc.__context__).__name__, 80)
            if (exc.__cause__ or exc.__context__) is not None else "",
            "cause": clean_text(exc.__cause__ or exc.__context__),
            "stage": clean_text(stage, 40),
            "provider": clean_text(provider, 80),
            "model": clean_text(model, 80),
            "elapsed_ms": max(0, min(int(elapsed_ms), 600_000)),
            "status_code": reported_status if isinstance(reported_status, int) else None,
            "retry": bool(retry),
        }
        path = _journal_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > _MAX_BYTES:
            path.replace(path.with_name(_JOURNAL + ".1"))
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        return record
    except (OSError, TypeError, ValueError):
        return {}
