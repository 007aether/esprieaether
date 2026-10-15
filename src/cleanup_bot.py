#!/usr/bin/env python3
"""
cleanup_bot.py — disk cleanup: old logs, temp archives, git gc

WHAT: Frees disk on the C: drive by removing:
  - log files older than N days (esprieaether + Sunna workspaces)
  - ollama pull cache, WinGet cache, npm cache
  - *.zip / *.tar.gz archives in Temp older than N days
  - runs `git gc --prune=now` on both repos

WHY: C: sits at 82-85% with the colibri model download running; a full disk
silently kills services and blocks new model downloads. Runs from the
autonomous loop daily and reports freed MB.

Usage:
  python cleanup_bot.py            # dry run (report only)
  python cleanup_bot.py --apply    # actually delete
  python cleanup_bot.py --days 3   # log age threshold (default 3)
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", HOME / "AppData" / "Local"))
TEMP = LOCALAPPDATA / "Temp"

REPOS = [
    HOME / "Desktop" / "esprieaether",
    HOME / "Desktop" / "Sunna-Equipe-Industrial",
]
LOG_DIRS = [
    HOME / "Desktop" / "esprieaether" / "data" / "logs",
    HOME / "ESPRIEAETHER" / "data" / "logs",
    HOME / "Desktop" / "Sunna-Equipe-Industrial" / "Veille" / "logs",
    HOME / "Desktop" / "Sunna-Equipe-Industrial" / "Recherche",
]
CACHE_DIRS = [
    TEMP / "ollama_p",
    TEMP / "WinGet",
    LOCALAPPDATA / "npm-cache",
    TEMP / "cprof2",
]


def dir_size(path: Path) -> int:
    total = 0
    try:
        for p in path.rglob("*"):
            try:
                if p.is_file():
                    total += p.stat().st_size
            except OSError:
                pass
    except OSError:
        pass
    return total


def clean_old_logs(days=3, apply=False):
    freed = 0
    removed = 0
    cutoff = time.time() - days * 86400
    for d in LOG_DIRS:
        if not d.exists():
            continue
        for f in d.rglob("*.log"):
            try:
                if f.stat().st_mtime < cutoff:
                    freed += f.stat().st_size
                    removed += 1
                    if apply:
                        f.unlink()
            except OSError:
                pass
        for f in d.rglob("*.err"):
            try:
                if f.stat().st_mtime < cutoff:
                    freed += f.stat().st_size
                    removed += 1
                    if apply:
                        f.unlink()
            except OSError:
                pass
    return {"freed": freed, "removed": removed, "what": "old logs"}


def clean_temp_archives(days=3, apply=False):
    freed = 0
    removed = 0
    cutoff = time.time() - days * 86400
    if TEMP.exists():
        for f in TEMP.glob("*.zip"):
            try:
                if f.stat().st_mtime < cutoff:
                    freed += f.stat().st_size
                    removed += 1
                    if apply:
                        f.unlink()
            except OSError:
                pass
        for f in TEMP.glob("*.tar.gz"):
            try:
                if f.stat().st_mtime < cutoff:
                    freed += f.stat().st_size
                    removed += 1
                    if apply:
                        f.unlink()
            except OSError:
                pass
    return {"freed": freed, "removed": removed, "what": "temp archives"}


def clean_caches(apply=False):
    freed = 0
    removed = 0
    for d in CACHE_DIRS:
        if d.exists():
            size = dir_size(d)
            freed += size
            removed += 1
            if apply:
                try:
                    shutil.rmtree(d, ignore_errors=True)
                except Exception:
                    pass
    return {"freed": freed, "removed": removed, "what": "caches (ollama/WinGet/npm)"}


def git_gc(apply=False):
    freed = 0
    for repo in REPOS:
        if not (repo / ".git").exists():
            continue
        before = dir_size(repo / ".git")
        if apply:
            try:
                subprocess.run(
                    ["git", "gc", "--prune=now", "--quiet"],
                    cwd=str(repo), timeout=120,
                    capture_output=True,
                )
            except Exception:
                pass
        after = dir_size(repo / ".git")
        freed += max(0, before - after)
    return {"freed": freed, "removed": 0, "what": "git gc"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually delete (default: dry run)")
    ap.add_argument("--days", type=int, default=3)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    results = [
        clean_old_logs(days=args.days, apply=args.apply),
        clean_temp_archives(days=args.days, apply=args.apply),
        clean_caches(apply=args.apply),
        git_gc(apply=args.apply),
    ]

    total = sum(r["freed"] for r in results)
    total_removed = sum(r["removed"] for r in results)

    if args.json:
        print(json.dumps({
            "mode": "apply" if args.apply else "dry-run",
            "freed_mb": round(total / 1024 / 1024, 1),
            "removed_count": total_removed,
            "details": results,
        }, ensure_ascii=False))
    else:
        mode = "APPLIED" if args.apply else "DRY RUN"
        print(f"🧹 cleanup [{mode}] — freed {total / 1024 / 1024:.1f} MB ({total_removed} items)")
        for r in results:
            print(f"   {r['what']}: {r['freed'] / 1024 / 1024:.1f} MB ({r['removed']} items)")


if __name__ == "__main__":
    main()
