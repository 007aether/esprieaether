#!/usr/bin/env python3
"""
ESPRIEAETHER AUTO-MONITORING & AUTO-REPLY SYSTEM
=================================================
Automated health monitoring + weekly report generator.
Runs as a cron job every hour.

Features:
  - Checks all 8 services (5000, 5001, 5102, 5103, 5104, 11435, 11436, 11437)
  - Logs health status to data/monitor.log
  - Auto-reports problems via Hermes bridge
  - Generates weekly report at midnight
  - Sends alerts to Telegram if critical service down
"""

import json
import os
import sys
import time
import urllib.request
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
ESPRIEAETHER_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ESPRIEAETHER_DIR / "data"
LOG_DIR = Path(os.path.expanduser("~")) / "ESPRIEAETHER" / "data"
LOG_FILE = LOG_DIR / "monitor.log"

# ── Services to monitor ────────────────────────────────────────────────
SERVICES = {
    "web": {"port": 5000, "name": "EsprieAether Web"},
    "cloud_desktop": {"port": 5001, "name": "Cloud Desktop"},
    "integrations": {"port": 5102, "name": "Integrations"},
    "kanban": {"port": 5103, "name": "Kanban"},
    "homedock": {"port": 5104, "name": "HomeDock"},
    "router": {"port": 11435, "name": "Router"},
    "orchestrator": {"port": 11436, "name": "Orchestrator"},
    "agent_mesh": {"port": 11437, "name": "Agent Mesh"},
}

# Hermes bridge
HERMES_BRIDGE = ESPRIEAETHER_DIR / "src" / "hermes_bridge_new.py"


def check_service(port: int) -> bool:
    """Check if a service is responding on a port."""
    try:
        req = urllib.request.Request(f"http://localhost:{port}/health")
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def check_all_services() -> dict:
    """Check all services and return status."""
    results = {}
    for key, svc in SERVICES.items():
        results[key] = {
            "name": svc["name"],
            "port": svc["port"],
            "status": "up" if check_service(svc["port"]) else "down",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    return results


def log_status(status: dict):
    """Write health log entry."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    line = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": status,
        "all_up": all(s["status"] == "up" for s in status.values()),
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return line


def notify_hermes(message: str):
    """Send a notification via Hermes bridge."""
    try:
        import subprocess
        subprocess.run(
            ["python3", str(ESPRIEAETHER_DIR / "src" / "hermes_bridge_new.py"),
             "--task", message],
            capture_output=True, timeout=30
        )
    except Exception:
        pass  # Silent fail - don't block the health check


def generate_weekly_report() -> dict:
    """Generate weekly report with summary stats."""
    stats = {
        "week": datetime.now(timezone.utc).isocalendar(),
        "generated": datetime.now(timezone.utc).isoformat(),
        "services": {},
        "metrics": {
            "services_up": 0,
            "services_total": len(SERVICES),
        },
    }

    health = check_all_services()
    for key, svc in health.items():
        stats["services"][key] = svc["status"]
        if svc["status"] == "up":
            stats["metrics"]["services_up"] += 1

    # Read agent board
    board_path = ESPRIEAETHER_DIR / "data" / "agent_board.json"
    if board_path.exists():
        try:
            with open(board_path, encoding="utf-8") as f:
                board = json.load(f)
            stats["agent_board_count"] = len(board) if isinstance(board, list) else 0
        except Exception:
            stats["agent_board_count"] = 0

    # Read knowledge base
    kb_path = ESPRIEAETHER_DIR / "data" / "knowledge_base" / "knowledge_index.json"
    if kb_path.exists():
        try:
            with open(kb_path, encoding="utf-8") as f:
                kb = json.load(f)
            stats["knowledge_base_items"] = len(kb.get("items", []))
        except Exception:
            stats["knowledge_base_items"] = 0

    return stats


def send_weekly_report():
    """Send weekly report to Hermes bridge."""
    report = generate_weekly_report()
    message = f"📊 أسبوعي الملخص (ESPRIEAETHER):\n"
    message += f"• الخدمات المتوفرة: {report['metrics']['services_up']}/{report['metrics']['services_total']}\n"
    message += f"• عدد وكالات النضام: {report.get('agent_board_count', 0)}\n"
    message += f"• الملفات في قاعدة المعرفة: {report.get('knowledge_base_items', 0)}\n"
    message += f"• التقرير: {report['generated']}\n"
    notify_hermes(message)
    # Also save to file
    report_path = DATA_DIR / "weekly_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report


def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="EsprieAether Auto-Monitor")
    parser.add_argument("--check", action="store_true", help="Check all services")
    parser.add_argument("--report", action="store_true", help="Generate weekly report")
    parser.add_argument("--all", action="store_true", help="Check + generate report")
    args = parser.parse_args()

    if args.all or args.check:
        status = check_all_services()
        log_status(status)
        print("📊 Service Check:")
        for key, svc in status.items():
            status_icon = "🟢" if svc["status"] == "up" else "🔴"
            print(f"  {status_icon} {svc['name']} (port {svc['port']}): {svc['status']}")

        if not all(s["status"] == "up" for s in status.values()):
            notify_hermes("❌ CRITICAL: Some services are down!")
            print("\n⚠️  Some services are DOWN!")
            return 1

        print("\n✅ All services healthy!")
        if args.all:
            send_weekly_report()
            print("🗓️  Weekly report generated and synced to Hermes")

    elif args.report:
        report = send_weekly_report()
        print(f"🗓️  Weekly Report Generated:")
        print(f"  • Services: {report['metrics']['services_up']}/{report['metrics']['services_total']}")
        print(f"  • Generated: {report['generated']}")
        return 0

    return 0


if __name__ == "__main__":
    main()
