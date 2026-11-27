#!/usr/bin/env python3
"""J152 — جلب 20 مشروعاً من تقرير آخر 7 أيام، بتنزيل محلي معزول.

القراءة من ``state/github_week_report.json`` (تقرير جاهز، HTTPS للقراءة فقط).
التنزيل ``git clone --depth 1`` إلى ``state/imported_projects/`` — مجلد مستبعد
من Git والمانيفست. ما كاين أي pip/npm install، أي submodule، ولا تنفيذ سكربت
تنصيب من مستودع مجهول؛ هادشي كيبقى قرار منفصل وموافقة منفصلة.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_STATE_DIR = BASE_DIR / "state"
WEEK_REPORT = "github_week_report.json"
REPORT_NAME = "github_projects_report.json"
PROJECTS_DIR = "imported_projects"
TARGET = 20
API_HOST = "github.com"

# مشاريع اختارها المالك بالاسم من تقرير آخر 7 أيام: محلية، صوت، وكلاء ذاتيين.
PRIORITY_NAMES = (
    "w01fb0ss/PiBot",
    "sous-labs/songe",
    "enwove/flyx",
    "CajasiZep76/local-ai-chat-uncensored",
    "Powerdaalembic/LocalAI-VRAMReadyCheck",
    "hectorandac/laura-voice",
    "Anarki-LNX/nuorb",
    "rodrigo2024134442/max-assistant",
    "jackby03/homeserver-assistant",
    "Teaspoon-AI/teaport",
    "deval1995-creator/jarvis",
    "GabrielBeckler/JARVIS-AI-ASSISTENT",
    "NerdoBaggins/agent-orb",
    "jcafazzo/self-improving-agent-skills",
    "travisim/awesome-self-improving-agents",
    "Sumit1153/-self-improving-ai-agent-harness",
    "Hakkixxx/self-improving-skills",
    "MoritzPindorek/Five-Laws-of-AI-Agents",
    "aiengineeringinsider/ragas-deepeval",
    "plannotator/talkto",
)

# مستودعات خارج الموضوع أو بمخاطرة واضحة: ما كندownloadّوهومش.
RISKY = (
    "airdrop", "offer-subscription", "rooted", "wallet", "testnet",
    "simulator", "theater", "interview-questions", "neonclipping",
    "koboldcpp-1-125", "unfiltered", "video-generation", "data-extraction",
    "advocacy-cloud", "trending-self-improving", "coding-agents",
    "attack-detections", "openman", "web-social",
)

USEFUL_WORDS = (
    "local", "offline", "voice", "llm", "agent", "mcp", "gguf", "llama",
    "self-improving", "speech", "privacy", "private", "memory", "eval",
    "desktop", "linux", "windows", "android", "home", "tool",
)

_secret = re.compile(r"(?i)\b(?:token|password|secret|api[_-]?key)\b\s*[:=]\s*\S+")


def _clean(text: object, limit: int = 160) -> str:
    value = _secret.sub("[redacted]", str(text if text is not None else ""))
    return re.sub(r"\s+", " ", value).strip()[:limit]


def _is_risky(name: str) -> bool:
    lowered = name.lower()
    return any(marker in lowered for marker in RISKY)


def _score(row: dict) -> tuple[int, int]:
    name = str(row.get("name") or "")
    description = str(row.get("description") or "").lower()
    priority = PRIORITY_NAMES.index(name) if name in PRIORITY_NAMES else -1
    words = sum(1 for word in USEFUL_WORDS if word in description)
    try:
        stars = int(row.get("stars") or 0)
    except (TypeError, ValueError):
        stars = 0
    return (1000 - priority if priority >= 0 else words, stars)


def select(items: list[dict], limit: int = TARGET) -> list[dict]:
    """اختار مشاريع مفيدة من تقرير الأسبوع، بلا تكرار وبلا مستودعات خطرة."""
    seen: set[str] = set()
    kept: list[dict] = []
    for row in items:
        name = str(row.get("name") or "").strip()
        url = str(row.get("url") or "").strip()
        if not name or not url or name in seen or _is_risky(name):
            continue
        if not url.startswith("https://" + API_HOST + "/"):
            continue
        seen.add(name)
        kept.append({
            "name": name,
            "url": url,
            "description": _clean(row.get("description")),
            "reason": "اختيار المالك من تقرير آخر 7 أيام" if name in PRIORITY_NAMES
                      else "مشروع محلي/صوت/وكيل مفيد",
            "stars": row.get("stars", 0),
        })
    kept.sort(key=lambda row: (_score(row), row["name"]), reverse=True)
    return kept[:max(0, min(int(limit), TARGET))]


def validate_url(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(str(url or ""))
    except ValueError as exc:
        raise ValueError("invalid_github_url") from exc
    if parsed.scheme != "https" or (parsed.hostname or "").lower() != API_HOST:
        raise ValueError("host_not_allowed")
    if parsed.username or parsed.password or parsed.port or parsed.query or parsed.fragment:
        raise ValueError("url_not_allowed")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2 or any(part in (".", "..") for part in parts):
        raise ValueError("repo_path_not_allowed")
    return "https://" + API_HOST + "/" + parts[0] + "/" + parts[1]


def clone_command(git_exe: str, url: str, dest: Path) -> list[str]:
    safe_url = validate_url(url)
    return [
        "-c", "safe.directory=*", "-c", "core.longpaths=true",
        "clone", "--depth", "1", "--quiet", "--no-tags",
        "-c", "core.hooksPath=/dev/null",
        safe_url, str(dest),
    ]


def write_report(state: Path, selected: list[dict], results: list[dict]) -> dict:
    by_name = {row["name"]: row for row in results}
    projects = []
    for row in selected:
        outcome = by_name.get(row["name"], {})
        projects.append({
            "name": row["name"],
            "url": row["url"],
            "reason": row["reason"],
            "status": outcome.get("status", "not_available"),
            "detail": _clean(outcome.get("detail", "no_result")),
        })
    ok = bool(projects) and all(row["status"] == "live_verified" for row in projects)
    report = {
        "checkedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "live_verified" if ok else (
            "implemented_unverified" if any(row["status"] == "live_verified" for row in projects)
            else "not_available"
        ),
        "count": len(projects),
        "projects": projects,
    }
    state.mkdir(parents=True, exist_ok=True)
    path = state / REPORT_NAME
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    return report


def clone_many(
    state: Path,
    selected: list[dict],
    git_exe: str | None = None,
    dest_root: Path | None = None,
    runner=None,
) -> dict:
    git_exe = git_exe or str(Path(__file__).resolve().parents[1].parent / ".tools" / "git" / "cmd" / "git.exe")
    dest_root = dest_root or (state / PROJECTS_DIR)
    dest_root.mkdir(parents=True, exist_ok=True)
    run = runner or subprocess.run
    results: list[dict] = []
    for row in selected:
        owner, _, repo = row["name"].partition("/")
        dest = dest_root / (owner + "__" + repo.replace("/", "_"))
        try:
            command = clone_command(git_exe, row["url"], dest)
        except ValueError as exc:
            results.append({"name": row["name"], "status": "not_available", "detail": str(exc)})
            continue
        if (dest / ".git").exists():
            results.append({"name": row["name"], "status": "live_verified", "detail": "already_present"})
            continue
        try:
            proc = run(
                [str(git_exe)] + command,
                capture_output=True, text=True, timeout=180,
                env={**dict(__import__("os").environ), "GIT_TERMINAL_PROMPT": "0"},
                cwd=str(dest_root),
            )
            detail = proc.stderr if getattr(proc, "returncode", 1) == 0 else (
                getattr(proc, "stderr", "") or getattr(proc, "stdout", "")
            )
            status = "live_verified" if (
                getattr(proc, "returncode", 1) == 0 and (dest / ".git").exists()
            ) else "not_available"
            results.append({"name": row["name"], "status": status, "detail": _clean(detail or status)})
        except Exception as exc:  # timeout, git absent, disque plein
            results.append({"name": row["name"], "status": "not_available", "detail": _clean(exc)})
    return write_report(state, selected, results)


def _say(text: str) -> None:
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


def main(state_dir: Path | None = None) -> None:
    state = Path(state_dir or DEFAULT_STATE_DIR)
    source = state / WEEK_REPORT
    if not source.exists():
        _say("ما كاينش تقرير الأسبوع: " + str(source))
        return
    payload = json.loads(source.read_text(encoding="utf-8"))
    selected = select(payload.get("items", []))
    report = clone_many(state, selected)
    ok = sum(1 for row in report["projects"] if row["status"] == "live_verified")
    _say("مشاريع GitHub: " + str(ok) + "/" + str(report["count"]) + " تنزّلات، الحالة: " + report["status"])
    _say("التقرير: " + str(state / REPORT_NAME))


if __name__ == "__main__":
    main()
