#!/usr/bin/env python3
"""
cloud_agent.py — EsprieAether running FREE on GitHub Actions (the "free VPS")

WHAT: The PC is one node; GitHub Actions is the second node. This script runs
on GitHub's ubuntu runners every 6 hours (and on every GitHub Issue = remote
command), so the system keeps thinking when the PC is off, and the user can
drive it from a phone by opening a GitHub Issue.

WHY: a VPS costs €5/month. GitHub Actions minutes are free for public repos,
and GitHub Issues are a free remote-control channel (open an issue from the
phone → the PC-side poller reads it → executes → comments back).

MODES:
  issue     — an Issue was opened. Parse its body as a command:
              "mesh cycle", "scan", "status", "board", "sync pc"
              Reply in a comment, close the issue.
  scheduled — 6-hour cycle: airdrop scan + mesh-free status snapshot.
              Writes data/cloud_status.json, which the PC reads over git.
  manual    — workflow_dispatch action: status / scan / health.

OUTPUTS (all committed back to the repo, so the PC reads them via git pull):
  data/cloud_status.json     — last cloud run: timestamp, results
  data/cloud_commands.json   — commands the PC should execute (PC poller reads)
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
DATA.mkdir(exist_ok=True)

GITHUB_TOKEN = os.getenv("GH_TOKEN", "")
ISSUE_NUMBER = os.getenv("ISSUE_NUMBER", "")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def gh_request(path, method="GET", payload=None):
    """GitHub REST API call (token available in Actions env)."""
    if not GITHUB_TOKEN:
        return None
    url = f"https://api.github.com/repos/{os.getenv('GITHUB_REPOSITORY', '007aether/esprieaether')}{path}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  ⚠ GitHub API: {e}")
        return None


def comment_issue(number, body):
    return gh_request(f"/issues/{number}/comments", "POST", {"body": body})


def close_issue(number):
    return gh_request(f"/issues/{number}", "PATCH", {"state": "closed"})


# ── Cloud capabilities (what can run WITHOUT the PC) ──

def cloud_airdrop_scan():
    """Scan airdrop RSS feeds — pure network, no local model needed."""
    feeds = [
        "https://airdropalert.com/feed",
        "https://airdrops.io/feed/",
    ]
    items = []
    for url in feeds:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "aether-cloud"})
            with urllib.request.urlopen(req, timeout=20) as r:
                text = r.read().decode("utf-8", "replace")
            # crude RSS title extraction (stdlib only on the runner)
            import re
            titles = re.findall(r"<title>(?:<!\[CDATA\[)?(.+?)(?:\]\]>)?</title>", text)
            for t in titles[1:15]:  # skip channel title
                if len(t) > 8:
                    items.append({"title": t.strip()[:120], "source": url})
        except Exception as e:
            items.append({"title": f"feed error: {e}", "source": url})
        time.sleep(1)
    return items


def cloud_status_snapshot():
    """What the cloud node knows — PC health is read from the last git state."""
    status_file = DATA / "cloud_status.json"
    last = {}
    if status_file.exists():
        try:
            last = json.loads(status_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "cloud_ok": True,
        "cloud_last_run": now_iso(),
        "pc_last_seen": last.get("pc_last_seen", "unknown"),
        "note": "cloud node alive — PC reads this via git pull",
    }


def write_cloud_status(data):
    status_file = DATA / "cloud_status.json"
    prev = {}
    if status_file.exists():
        try:
            prev = json.loads(status_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    prev.update(data)
    prev["cloud_last_run"] = now_iso()
    status_file.write_text(json.dumps(prev, ensure_ascii=False, indent=2), encoding="utf-8")
    return prev


def queue_pc_command(command, params=None):
    """Queue a command for the PC-side poller (autonomous_loop reads it)."""
    cmds_file = DATA / "cloud_commands.json"
    cmds = []
    if cmds_file.exists():
        try:
            cmds = json.loads(cmds_file.read_text(encoding="utf-8"))
        except Exception:
            cmds = []
    cmds.append({
        "command": command,
        "params": params or {},
        "ts": now_iso(),
        "executed": False,
    })
    cmds_file.write_text(json.dumps(cmds[-20:], ensure_ascii=False, indent=2), encoding="utf-8")
    return cmds[-1]


# ── Modes ──

def mode_issue(issue_number, issue_body):
    """Remote control: an Issue body is a command."""
    body = (issue_body or "").strip().lower()
    reply_lines = [f"☁️ **Aether Cloud Agent** — {now_iso()}\n"]

    if "mesh" in body or "cycle" in body:
        # The cloud cannot run the local mesh (needs Ollama) — queue it for the PC
        queued = queue_pc_command("mesh_cycle", {"source": "issue"})
        reply_lines.append(
            "🕸️ دورة الوكلاء مطلوبة — مبرمجة على الـ PC (الـ mesh كيخدم محلي مع Ollama).\n"
            f"الأمر ف الطابور: `{queued['command']}`"
        )
    elif "scan" in body or "airdrop" in body:
        items = cloud_airdrop_scan()
        write_cloud_status({"last_scan": items[:20], "scan_count": len(items)})
        reply_lines.append(f"📡 فحص الإيردروبات (سحابي): **{len(items)}** عنصر")
        for it in items[:8]:
            reply_lines.append(f"• {it['title'][:80]}")
    elif "status" in body:
        snap = cloud_status_snapshot()
        write_cloud_status(snap)
        reply_lines.append("📊 حالة السحابة:")
        reply_lines.append(f"```json\n{json.dumps(snap, ensure_ascii=False, indent=2)}\n```")
    elif "board" in body:
        board_file = DATA / "agent_board.json"
        if board_file.exists():
            board = json.loads(board_file.read_text(encoding="utf-8"))
            reply_lines.append(f"🕸️ لوحة الوكلاء (آخر {min(8, len(board))} رسائل):")
            for m in board[-8:]:
                reply_lines.append(f"• `{m['agent']}`: {m['text'][:70]}")
        else:
            reply_lines.append("📭 اللوحة فارغة")
    else:
        reply_lines.append(
            "الأوامر المتاحة:\n"
            "• `mesh cycle` — دورة الوكلاء (تتنفذ على الـ PC)\n"
            "• `scan` — فحص الإيردروبات (سحابي)\n"
            "• `status` — حالة السحابة\n"
            "• `board` — لوحة الوكلاء"
        )

    comment_issue(issue_number, "\n".join(reply_lines))
    close_issue(issue_number)
    print(f"  ✅ issue #{issue_number} answered + closed")


def mode_scheduled():
    """6-hour cloud cycle: scan + snapshot, committed back to the repo."""
    print("☁️ scheduled cloud cycle")
    items = cloud_airdrop_scan()
    snap = cloud_status_snapshot()
    snap["last_scan_count"] = len(items)
    snap["last_scan"] = items[:20]
    write_cloud_status(snap)
    print(f"  ✅ scan: {len(items)} items, status written")


def mode_manual(action):
    print(f"☁️ manual: {action}")
    if action == "scan":
        items = cloud_airdrop_scan()
        write_cloud_status({"last_scan": items[:20], "scan_count": len(items)})
        print(f"  {len(items)} items")
    elif action == "status":
        snap = cloud_status_snapshot()
        write_cloud_status(snap)
        print(f"  {json.dumps(snap, ensure_ascii=False)}")
    else:  # health
        print(f"  cloud alive {now_iso()}")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "status"
    if mode == "--mode":
        mode = sys.argv[2] if len(sys.argv) > 2 else "status"

    if mode == "issue":
        mode_issue(ISSUE_NUMBER, os.getenv("ISSUE_BODY", ""))
    elif mode == "scheduled":
        mode_scheduled()
    elif mode == "manual":
        action = "status"
        for i, a in enumerate(sys.argv):
            if a == "--action" and i + 1 < len(sys.argv):
                action = sys.argv[i + 1]
        mode_manual(action)
    else:
        print(f"unknown mode: {mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
