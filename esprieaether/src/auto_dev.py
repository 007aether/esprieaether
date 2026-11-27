#!/usr/bin/env python3
"""J152 — تطوير ذاتي محكوم: اختبارات خضرة + مسارات آمنة قبل أي commit/push.

القرار مكتوب فـ ``state/atulya/autonomy.json`` (auto_commit_push) و``ENV
SUNNAVOK_AUTO_COMMIT_PUSH=1``. ما كاينش force push، ولا rebase، ولا لمس للملفات
المحمية (.env، المفاتيح، touping.exe، state، .tools، .venv، models).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
ROOT = BASE_DIR.parent
DEFAULT_STATE_DIR = BASE_DIR / "state"
DEFAULT_GIT = ROOT / ".tools" / "git" / "cmd" / "git.exe"
DEFAULT_PYTHON = BASE_DIR / ".venv" / "Scripts" / "python.exe"
DEFAULT_NODE = ROOT / ".tools" / "node-v26.13.1" / "node.exe"

BANNED_NAMES = frozenset({
    ".env", "touping.exe", "secrets.enc", "credentials.json", "secrets.json",
    "freellmapi.key", "vault.key", "id_rsa", "id_ed25519",
})
BANNED_DIRS = frozenset({".tools", ".venv", "node_modules", "models", "state", ".git"})
BANNED_SUFFIX = (".key", ".pem", ".pfx", ".p12")

CHECKS = (
    ("node", str(DEFAULT_NODE), ["--test", "tests/autonomous_bot.test.mjs",
                                "tests/gsm_capability.test.mjs"]),
    ("python", str(DEFAULT_PYTHON), ["-m", "unittest", "tests.test_github_projects",
                                    "tests.test_auto_dev"]),
)

_secret = re.compile(r"(?i)\b(?:token|password|secret|api[_-]?key)\b\s*[:=]\s*\S+")


def _clean(value: object, limit: int = 200) -> str:
    return _secret.sub("[redacted]", re.sub(r"\s+", " ", str(value or "")).strip())[:limit]


def protected(paths: list[str]) -> str | None:
    """أول مسار ممنوع، أو None يلا كان الكل آمناً."""
    for raw in paths:
        path = str(raw).strip().replace("\\", "/")
        while path.startswith("./"):
            path = path[2:]
        path = path.lstrip("/")
        parts = [part.lower() for part in path.split("/") if part]
        if not parts:
            continue
        if parts[0] in BANNED_DIRS or any(part in BANNED_DIRS for part in parts[:-1]):
            return raw
        if parts[-1] in BANNED_NAMES or parts[-1].endswith(BANNED_SUFFIX):
            return raw
    return None


def changed_files(root: Path, git_exe: str, runner) -> list[str]:
    proc = runner(
        [str(git_exe), "-c", "safe.directory=*", "status", "--porcelain=v1", "-z"],
        cwd=str(root), capture_output=True, text=True, timeout=60,
    )
    names = []
    for entry in str(proc.stdout or "").split("\0"):
        if not entry:
            continue
        name = entry[3:] if len(entry) > 3 and entry[2] == " " else entry
        names.append(name.strip())
    return [name for name in names if name]


def verify(root: Path, runner) -> dict:
    results = []
    ok = True
    for name, exe, args in CHECKS:
        if not Path(exe).exists():
            results.append({"name": name, "ok": False, "detail": "runner_missing"})
            ok = False
            continue
        proc = runner([exe] + args, cwd=str(root), capture_output=True, text=True, timeout=300)
        passed = int(getattr(proc, "returncode", 1)) == 0
        ok = ok and passed
        results.append({"name": name, "ok": passed,
                        "detail": _clean(getattr(proc, "stderr", "") or getattr(proc, "stdout", ""))})
    return {"ok": ok, "checks": results}


def next_j(root: Path, git_exe: str, runner) -> int:
    proc = runner(
        [str(git_exe), "-c", "safe.directory=*", "log", "-50", "--format=%s"],
        cwd=str(root), capture_output=True, text=True, timeout=60,
    )
    numbers = []
    for line in str(proc.stdout or "").splitlines():
        match = re.match(r"\s*J(\d+)\b", line)
        if match:
            numbers.append(int(match.group(1)))
    return (max(numbers) if numbers else 151) + 1


def commit_and_push(root: Path, git_exe: str, message: str, runner, status=None) -> dict:
    paths = list(status) if status is not None else changed_files(root, git_exe, runner)
    if not paths:
        return {"status": "no_changes", "paths": [], "checkedAt": _now()}
    bad = protected(paths)
    if bad:
        return {"status": "blocked", "reason": "protected_path", "path": bad,
                "paths": paths, "checkedAt": _now()}
    checks = verify(root, runner)
    if not checks["ok"]:
        return {"status": "blocked", "reason": "tests_failed", "checks": checks["checks"],
                "paths": paths, "checkedAt": _now()}
    for verb, args in (("add", ["add", "-A"]),
                       ("commit", ["commit", "-m", message]),
                       ("push", ["push"])):
        proc = runner(
            [str(git_exe), "-c", "safe.directory=*"] + args,
            cwd=str(root), capture_output=True, text=True, timeout=180,
        )
        if int(getattr(proc, "returncode", 1)) != 0:
            return {"status": "failed", "step": verb, "detail": _clean(
                getattr(proc, "stderr", "") or getattr(proc, "stdout", "")),
                "paths": paths, "checkedAt": _now()}
    return {"status": "pushed", "paths": paths, "message": message, "checkedAt": _now()}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_report(state_dir: Path, outcome: dict) -> dict:
    report = {"checkedAt": _now(), **outcome}
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / "auto_dev_state.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    return report


def maybe_commit_push(
    state_dir: Path | None = None,
    root: Path | None = None,
    runner=None,
    enabled: bool | None = None,
    git_exe: str | None = None,
) -> dict:
    state_dir = Path(state_dir or DEFAULT_STATE_DIR)
    root = Path(root or ROOT)
    git_exe = str(git_exe or DEFAULT_GIT)
    runner = runner or subprocess.run
    if enabled is None:
        enabled = os.environ.get("SUNNAVOK_AUTO_COMMIT_PUSH") == "1"
    if not enabled:
        return write_report(state_dir, {"status": "disabled", "reason": "env_not_set"})
    autonomy = state_dir / "atulya" / "autonomy.json"
    try:
        allowed = json.loads(autonomy.read_text(encoding="utf-8")).get("auto_commit_push") is True
    except (OSError, ValueError):
        allowed = False
    if not allowed:
        return write_report(state_dir, {"status": "disabled", "reason": "owner_not_opted_in"})
    try:
        number = next_j(root, git_exe, runner)
        outcome = commit_and_push(
            root, git_exe, f"J{number}: auto-dev — tests verts", runner,
        )
    except Exception as exc:  # réseau, git absent, disque plein
        outcome = {"status": "failed", "detail": _clean(exc)}
    return write_report(state_dir, outcome)


def main() -> None:
    report = maybe_commit_push()
    print(json.dumps({"status": report["status"], "reason": report.get("reason", "")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
