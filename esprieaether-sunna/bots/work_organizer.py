#!/usr/bin/env python3
"""
work_organizer.py — INTEGRATION ROADMAP & WORK-QUEUE ORGANIZER
============================================================

WHAT IT DOES
------------
1. Reads  data/integration_roadmap.json — or creates it with a seeded list of
   integration items {name, source (repo/url), status, priority 1-5,
   next_action, owner_agent, updated_at, note} — and keeps the file sorted by
   priority (lowest number = highest priority).
2. Organizes the *open* items into data/work_queue.json, split into two
   sections, each sorted by priority then updated_at:
       NEXT_ACTIONS  — what to do next
       ISSUES        — what needs fixing / unblocking
3. When run as __main__, prints a plain-text Telegram-style report of the queue
   and writes data/work_organizer_status.json with the snapshot.

STATUS WORD BOOK
----------------
  open / todo / pending / wip          -> NEXT_ACTIONS
  issue / blocked / needs-fix / fixme  -> ISSUES
  done / complete / closed / archived  -> skipped

USAGE
-----
    python work_organizer.py            # (re)seed roadmap + build queue + report
    python work_organizer.py --status   # print the status snapshot only
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ROADMAP_FILE = DATA_DIR / "integration_roadmap.json"
WORK_QUEUE_FILE = DATA_DIR / "work_queue.json"
STATUS_FILE = DATA_DIR / "work_organizer_status.json"

# Default field values for roadmap items that are missing data.
DEFAULT_STATUS = "open"
DEFAULT_PRIORITY = 3
DEFAULT_NEXT_ACTION = "Review and start"
DEFAULT_OWNER = "work_organizer"
DEFAULT_NOTE = ""

# Items that are finished and should not appear in the queue.
STATUS_DONE = {"done", "complete", "closed", "archived"}

# Items that need attention / fixing; they land under ISSUES.
STATUS_ISSUE = {"issue", "blocked", "needs-fix", "needs_unblock", "fixme"}


def utcnow_iso():
    """Current UTC timestamp in ISO-8601."""
    return datetime.now(timezone.utc).isoformat()


def default_item(name, source, **overrides):
    """Build a normalized roadmap item dict with defaults filled in."""
    return {
        "name": name,
        "source": source,
        "status": overrides.pop("status", DEFAULT_STATUS),
        "priority": overrides.pop("priority", DEFAULT_PRIORITY),
        "next_action": overrides.pop("next_action", DEFAULT_NEXT_ACTION),
        "owner_agent": overrides.pop("owner_agent", DEFAULT_OWNER),
        "updated_at": overrides.pop("updated_at", utcnow_iso()),
        "note": overrides.pop("note", DEFAULT_NOTE),
    }


# ---------------------------------------------------------------------------
# Seed entries (name, source, status, priority, next_action, owner_agent, note)
# ---------------------------------------------------------------------------
SEED = [
    default_item(
        "agent-skills", "anthropics/skills",
        status="open", priority=1,
        next_action="Audit agent-skill registry metadata",
        owner_agent="self_improve",
        note="agent-skills harness package from anthropics",
    ),
    default_item(
        "work-organizer", "local",
        status="open", priority=1,
        next_action="Review and start",
        owner_agent="work_organizer",
        note="Workspace organizer for integration tasks",
    ),
    default_item(
        "self-heal", "local",
        status="issue", priority=2,
        next_action="Restart watchdog services",
        owner_agent="self_improve",
        note="Services stall after a crash; watchdog does not restart them",
    ),
    default_item(
        "claude-mem", "local",
        status="open", priority=2,
        next_action="Review claude-mem truncation",
        owner_agent="jarvis_dev",
        note="Long memory entries get truncated in the router round-trip",
    ),
    default_item(
        "obsidian-vault", "local",
        status="issue", priority=3,
        next_action="Rebuild vault link graph",
        owner_agent="self_improve",
        note="Backlink graph out of sync after bulk edits",
    ),
    default_item(
        "five", "local",
        status="open", priority=3,
        next_action="Validate five-board sync",
        owner_agent="jarvis_dev",
        note="five-board connector sync jitter",
    ),
    default_item(
        "strix", "local",
        status="blocked", priority=3,
        next_action="Fix strix ingestion timeout",
        owner_agent="jarvis_dev",
        note="API key expired; awaiting credentials",
    ),
    default_item(
        "21st-magic-mcp", "github",
        status="open", priority=4,
        next_action="Smoke-test MCP handshake",
        owner_agent="jarvis_dev",
        note="MCP gateway smoke test",
    ),
    default_item(
        "fish-audio", "local",
        status="open", priority=4,
        next_action="Verify audio model download pipeline",
        owner_agent="jarvis_dev",
        note="Model download hangs mid-stream",
    ),
    default_item(
        "free-llm-apis", "local",
        status="issue", priority=5,
        next_action="Audit free-llm-apis key rotation",
        owner_agent="self_improve",
        note="Rotation endpoint silently drops expired keys",
    ),
]


def save_json(path, data, indent=1):
    """Write data as pretty JSON with UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=indent), encoding="utf-8")


def load_roadmap():
    """
    Load roadmap items.

    If data/integration_roadmap.json does not exist, create it from the seed
    (sorted by priority) and return the seed. Otherwise normalise whatever is
    already in the file and return it.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    if ROADMAP_FILE.exists():
        try:
            data = json.loads(ROADMAP_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                items = data
        except (ValueError, OSError):
            items = []

    if not items:
        items = [default_item(**s) for s in SEED]
        save_json(ROADMAP_FILE, items)
        return items

    return [normalize_item(it) for it in items]


def normalize_item(it):
    """Fill missing fields on an existing roadmap item with defaults."""
    if not isinstance(it, dict):
        return default_item("unknown", "local")
    return default_item(
        it.get("name", "unknown"),
        it.get("source", "local"),
        status=it.get("status", DEFAULT_STATUS),
        priority=it.get("priority", DEFAULT_PRIORITY),
        next_action=it.get("next_action", DEFAULT_NEXT_ACTION),
        owner_agent=it.get("owner_agent", DEFAULT_OWNER),
        updated_at=it.get("updated_at", utcnow_iso()),
        note=it.get("note", DEFAULT_NOTE),
    )


def sort_items(items):
    """Sort roadmap items by priority then updated_at (stable)."""
    return sorted(
        items,
        key=lambda i: (
            int(i.get("priority", DEFAULT_PRIORITY)),
            str(i.get("updated_at", "")),
        ),
    )


def organize(items):
    """
    Split items into NEXT_ACTIONS and ISSUES and sort each section by
    priority then updated_at.
    """
    next_actions = [
        i for i in items
        if i.get("status") not in STATUS_DONE and i.get("status") not in STATUS_ISSUE
    ]
    issues = [i for i in items if i.get("status") in STATUS_ISSUE]
    return {
        "NEXT_ACTIONS": sort_items(next_actions),
        "ISSUES": sort_items(issues),
    }


def build_status(queue):
    """Build the work_organizer_status.json snapshot."""
    return {
        "generated_at": utcnow_iso(),
        "roadmap_file": str(ROADMAP_FILE),
        "work_queue_file": str(WORK_QUEUE_FILE),
        "roadmap_total": len(sort_items(load_roadmap())),
        "open_total": len(queue["NEXT_ACTIONS"]) + len(queue["ISSUES"]),
        "next_action_count": len(queue["NEXT_ACTIONS"]),
        "issues_count": len(queue["ISSUES"]),
        "next_actions": queue["NEXT_ACTIONS"],
        "issues": queue["ISSUES"],
    }


def render_status(status):
    """Plain-text Telegram-style report of the queue."""
    L = []
    L.append("━" * 56)
    L.append("🌐  WORK ORGANIZER — STATUS REPORT")
    L.append("━" * 56)
    L.append("generated : {}".format(status["generated_at"]))
    L.append("roadmap   : {}".format(status["roadmap_file"]))
    L.append("queue     : {}".format(status["work_queue_file"]))
    L.append("open items: {}   |   next actions: {}   |   issues: {}".format(
        status["open_total"], status["next_action_count"], status["issues_count"]))
    L.append("━" * 56)
    L.append("NEXT ACTIONS — what to do next")
    if not status["next_actions"]:
        L.append("  (none)")
    for i, it in enumerate(status["next_actions"], 1):
        L.append("  {}. [P{} ] {}".format(i, it["priority"], it["name"]))
        L.append("      source : {}".format(it["source"]))
        L.append("      next   : {}".format(it["next_action"]))
        L.append("      owner  : {}".format(it["owner_agent"]))
        L.append("      note   : {}".format(it["note"]))
    L.append("ISSUES — what needs fixing")
    if not status["issues"]:
        L.append("  (none)")
    for i, it in enumerate(status["issues"], 1):
        L.append("  {}. [P{} ] {}".format(i, it["priority"], it["name"]))
        L.append("      source : {}".format(it["source"]))
        L.append("      next   : {}".format(it["next_action"]))
        L.append("      owner  : {}".format(it["owner_agent"]))
        L.append("      note   : {}".format(it["note"]))
    L.append("━" * 56)
    return "\n".join(L)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Integration roadmap & work queue organizer")
    ap.add_argument(
        "--status",
        action="store_true",
        help="print the status snapshot only (no files written)",
    )
    args = ap.parse_args(argv)

    items = load_roadmap()
    ordered = sort_items(items)
    save_json(ROADMAP_FILE, ordered)

    queue = organize(ordered)
    save_json(WORK_QUEUE_FILE, queue)

    status = build_status(queue)
    save_json(STATUS_FILE, status)

    print(render_status(status))
    print()
    print("✓ wrote {}".format(ROADMAP_FILE))
    print("✓ wrote {}".format(WORK_QUEUE_FILE))
    print("✓ wrote {}".format(STATUS_FILE))
    return 0


if __name__ == "__main__":
    main()
