#!/usr/bin/env python3
"""
self_improve.py — SELF-HEAL SYSTEM
لنظام EsprieAether
كانس الأخطاء، يشخصها، يتعلم منها، ويصلحها تلقائياً

WHAT: Scan logs for errors → diagnose → learn → propose fixes → apply
WHY: The autonomous loop generates errors; this system learns from them
      and prevents them from happening again.
"""

import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

LOG_DIR = BASE_DIR / "data" / "logs"
STATE_FILE = BASE_DIR / "data" / "self_improve_state.json"
ERROR_LOG_FILE = BASE_DIR / "data" / "self_improve_errors.json"

# Load state
if STATE_FILE.exists():
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
else:
    state = {
        "learned_patterns": {},
        "applied_fixes": [],
        "unknown_errors": [],
        "last_scan": None,
    }

# Load error log
if ERROR_LOG_FILE.exists():
    with open(ERROR_LOG_FILE, "r", encoding="utf-8") as f:
        error_log = json.load(f)
else:
    error_log = {"errors": [], "scan_count": 0}

logger = logging.getLogger("self_improve")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


# ── Pattern recognition ────────────────────────────────────────────

# Common error patterns → known causes → proposed fixes
ERROR_PATTERNS = {
    # Router errors
    "router.*11435.*connection": {
        "cause": "Router not responding or port conflict",
        "fix": "Restart ai_router.py service",
        "severity": "high",
        "learned": "Check port 11435 availability before starting router"
    },
    # Agent mesh errors
    "agent_mesh.*error": {
        "cause": "Agent mesh communication failure",
        "fix": "Restart agent_mesh.py service",
        "severity": "high",
        "learned": "Ensure all agents are registered in AGENTS dict"
    },
    # Memory errors
    "memory.*error": {
        "cause": "Vector memory database issue",
        "fix": "Check vector_memory.db integrity and reinitialize if needed",
        "severity": "medium",
        "learned": "Memory database should be backed up weekly"
    },
    # Port conflicts
    "address already in use": {
        "cause": "Port already in use by another process",
        "fix": "Kill conflicting process or use different port",
        "severity": "high",
        "learned": "Check port availability before starting new services"
    },
    # Import errors
    "No module named": {
        "cause": "Missing Python dependency",
        "fix": "Install missing module with pip",
        "severity": "medium",
        "learned": "Use requirements.txt for dependency management"
    },
    # Permissions errors
    "permission denied": {
        "cause": "File or directory permission issue",
        "fix": "Check file permissions and run with correct user",
        "severity": "medium",
        "learned": "Ensure proper file permissions for data/ and logs/"
    },
    # Disk space
    "no space left": {
        "cause": "Disk full",
        "fix": "Clean up disk space and archive old logs",
        "severity": "critical",
        "learned": "Run daily cleanup to prevent disk full"
    },
    # Process crashes
    "Traceback": {
        "cause": "Python exception in script",
        "fix": "Check traceback and fix the error",
        "severity": "high",
        "learned": "Add try/except blocks around risky operations"
    },
    # Timeout
    "timed out": {
        "cause": "Operation exceeded time limit",
        "fix": "Increase timeout or optimize the operation",
        "severity": "medium",
        "learned": "Always set reasonable timeouts for external calls"
    },
}


def categorize_error(error_text):
    """Categorize error based on patterns."""
    error_lower = error_text.lower()
    for pattern, info in ERROR_PATTERNS.items():
        if pattern.lower() in error_lower:
            return info, pattern
    return None, None


# ── Log scanning ───────────────────────────────────────────────────

def scan_logs():
    """Scan logs for errors."""
    errors = []
    log_dir = LOG_DIR

    if not log_dir.exists():
        return errors

    # Scan all log files
    for log_file in log_dir.glob("*.log"):
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                for i, line in enumerate(lines[-500:], start=1):  # last 500 lines
                    line_lower = line.lower()
                    if any(keyword in line_lower for keyword in ["error", "exception", "traceback", "failed", "denied", "timeout", "permission denied", "address already in use"]):
                        errors.append({
                            "file": str(log_file.name),
                            "line": i,
                            "text": line.strip(),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
        except Exception as e:
            logger.error(f"Error reading {log_file}: {e}")

    return errors


def load_executor_log():
    """Load executor log for error tracking."""
    log_file = BASE_DIR / "data" / "executor_log.json"
    if log_file.exists():
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def learn_from_errors(errors):
    """Learn from errors and categorize them."""
    learned = []
    unknown = []

    for error in errors:
        category, pattern = categorize_error(error["text"])
        if category:
            # Add to learned patterns
            if pattern not in state["learned_patterns"]:
                state["learned_patterns"][pattern] = {
                    "cause": category["cause"],
                    "fix": category["fix"],
                    "severity": category["severity"],
                    "count": 0,
                    "first_seen": datetime.now(timezone.utc).isoformat(),
                }
            state["learned_patterns"][pattern]["count"] += 1
            learned.append({
                "type": "learned",
                "pattern": pattern,
                "cause": category["cause"],
                "fix": category["fix"],
                "severity": category["severity"],
                "count": state["learned_patterns"][pattern]["count"],
            })
        else:
            unknown.append(error)

    # Update state
    state["last_scan"] = datetime.now(timezone.utc).isoformat()
    state["unknown_errors"].extend(unknown)

    # Save state
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    # Save errors
    with open(ERROR_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "errors": errors,
            "scan_count": state["learned_patterns"].get("count", 0),
        }, f, ensure_ascii=False, indent=2)

    return learned, unknown


def propose_fixes(learned):
    """Propose fixes for learned errors."""
    fixes = []
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
    return fixes


def apply_fix(fix):
    """Apply a fix."""
    action = fix["action"]
    pattern = fix["pattern"]
    fix_text = fix["fix"]

    if action == "immediate":
        # Restart affected service
        if "router" in pattern:
            import subprocess
            result = subprocess.run(
                ["pkill", "-f", "ai_router.py"],
                capture_output=True, text=True, timeout=5
            )
            import time
            time.sleep(2)
            result = subprocess.run(
                ["pkill", "-f", "ai_router.py"],
                capture_output=True, text=True, timeout=5
            )
            return {"status": "restarted", "service": "router", "msg": result.stdout[:200]}

        elif "agent_mesh" in pattern:
            import subprocess
            result = subprocess.run(
                ["pkill", "-f", "agent_mesh.py"],
                capture_output=True, text=True, timeout=5
            )
            import time
            time.sleep(2)
            result = subprocess.run(
                ["pkill", "-f", "agent_mesh.py"],
                capture_output=True, text=True, timeout=5
            )
            return {"status": "restarted", "service": "agent_mesh", "msg": result.stdout[:200]}

    return {"status": "skipped", "reason": "Manual review required"}


# ── Report generation ──────────────────────────────────────────────

def generate_report():
    """Generate a self-improve report."""
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scan_count": state.get("learned_patterns", {}).get("count", 0),
        "learned_patterns": len(state.get("learned_patterns", {})),
        "unknown_errors": len(state.get("unknown_errors", [])),
        "recent_errors": [],
        "fixes_applied": [],
    }

    # Get recent errors
    if ERROR_LOG_FILE.exists():
        with open(ERROR_LOG_FILE, "r", encoding="utf-8") as f:
            error_data = json.load(f)
            report["recent_errors"] = error_data.get("errors", [])[-10:]

    # Get learned patterns
    patterns = state.get("learned_patterns", {})
    report["learned_patterns"] = list(patterns.keys())[-20:]

    # Get fixes
    report["fixes_applied"] = state.get("applied_fixes", [])[-10:]

    # Generate summary
    summary = []
    if patterns:
        summary.append(f"✅ تعلمت {len(patterns)} نمط خطأ")
    if report["unknown_errors"]:
        summary.append(f"⚠️ {len(report['unknown_errors'])} خطأ غير معروف")
    if report["fixes_applied"]:
        summary.append(f"🛠️ {len(report['fixes_applied'])} إصلاح تطبيق")

    report["summary"] = " • ".join(summary) if summary else "لا توجد أخطاء"

    return report


# ── Main execution ────────────────────────────────────────────────

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Self-Improve System for EsprieAether")
    ap.add_argument("--once", action="store_true", help="Run one scan and exit")
    ap.add_argument("--daemon", action="store_true", help="Run as daemon (every 5 min)")
    ap.add_argument("--status", action="store_true", help="Show status report")
    ap.add_argument("--force", action="store_true", help="Force re-scan and apply fixes")
    args = ap.parse_args()

    if args.status:
        # Show status
        report = generate_report()
        print("📊 Self-Improve Report:")
        print(f"   Tümko: {report['generated_at']}")
        print(f"   Errors: {report['scan_count']}")
        print(f"   Tümko: {report['learned_patterns']}")
        print(f"   Unknown: {report['unknown_errors']}")
        print(f"   Summary: {report['summary']}")
        return

    # Scan logs
    errors = scan_logs()
    logger.info(f"🔍 Scanned logs: found {len(errors)} errors")

    if not errors:
        print("✅ No errors found. System is healthy.")
        return

    # Learn from errors
    learned, unknown = learn_from_errors(errors)
    logger.info(f"🧠 Learned {len(learned)} patterns, {len(unknown)} unknown")

    # Propose fixes
    fixes = propose_fixes(learned)
    logger.info(f"🛠️ Proposed {len(fixes)} fixes")

    # Apply fixes (if --force)
    if args.force:
        for fix in fixes:
            if fix["severity"] in ("critical", "high"):
                result = apply_fix(fix)
                logger.info(f"🔧 Applied fix for {fix['pattern']}: {result['status']}")
                state["applied_fixes"].append({
                    "pattern": fix["pattern"],
                    "fix": fix["fix"],
                    "result": result,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
    else:
        # Just show fixes
        print("🛠️ Proposed fixes:")
        for fix in fixes:
            print(f"   [{fix['severity']}] {fix['pattern']}: {fix['fix']}")

    if not args.force:
        print("\n💡 لم تعمل إصلاحات (استخدم --force لتفعيلها)")
        print("   أو شغّل: python self_improve.py --force")


if __name__ == "__main__":
    main()
