#!/usr/bin/env python3
"""
⚡ EsprieAether - Airdrop Intelligence (full module)
=====================================
📦 Modules:
  1. airdrop_agent.py     — RSS fetch + DB (airdrops.json) + Telegram format
  2. airdrop_scraper.py   — 5 source scrapers (airdrops.io, airdropalert, decrypt, etc.)
  3. airdrop_enricher.py  — deep_enrich via airdrops.io + GitHub stats
  4. airdrop_scorer.py    — A/B/C/D scoring + scam detection + format_telegram
  5. (new) airdrop_export.py — GitHub Issues export + CSV + Telegram notify

🎯 Goal: monitor airdrops, score, store, notify, export.
══════════════════════════════════════════════════════════════
Usage:
  python -m airdrop          # full run
  python airdrop_export.py   # export + notify (used by cloud bridge)
══════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import csv
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SRC = BASE_DIR / "src"
DATA = BASE_DIR / "data"
SCORED = DATA / "airdrop_scored.json"
SCORED_BACKUP = DATA / "airdrop_scored_backup.json"
AIRDROPS_DB = DATA / "airdrops.json"
EXPORT = DATA / "airdrop_export"

logger = logging.getLogger("airdrop_intel")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

# ── Paths ────────────────────────────────────────────────────────────────
if not EXPORT.exists():
    EXPORT.mkdir(parents=True, exist_ok=True)

# ── Import helpers ───────────────────────────────────────────────────────
sys_path = str(SRC)
if sys_path not in __import__("sys").path:
    __import__("sys").path.insert(0, SRC)

from airdrop_agent import AirdropAgent
from airdrop_scorer import score_all, top_candidates, format_telegram
from airdrop_agent import AirdropAgent as _Agent

# ── Export JSON ──────────────────────────────────────────────────────────
def export_json(out: Path | None = None) -> Path:
    """Persist scored airdrops (ranked) to JSON."""
    out = out or (EXPORT / "airdrop_scored.json")
    if not SCORED.exists():
        logger.warning("⚠️  scored.json missing — nothing to export")
        return out
    data = json.loads(SCORED.read_text(encoding="utf-8"))
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"✅ exported JSON → {out}  ({len(data.get('items', []))} items)")
    return out


# ── Export CSV ───────────────────────────────────────────────────────────
def export_csv(out: Path | None = None) -> Path:
    """Export top candidates to CSV (machine-readable)."""
    out = out or (EXPORT / "airdrop_top.csv")
    items = json.loads(SCORED.read_text(encoding="utf-8")).get("items", [])
    if not items:
        logger.warning("⚠️  no items to export")
        return out

    fieldnames = [
        "title", "link", "source", "date", "score", "grade", "signals",
        "flags", "has_github", "pay_to_play", "scored_at", "body",
    ]
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for it in sorted(items, key=lambda x: (-x.get("score", 0), x.get("date", ""))):
            w.writerow(it)
    logger.info(f"✅ exported CSV → {out}  ({len(items)} rows)")
    return out


# ── Export Markdown ──────────────────────────────────────────────────────
def export_md(out: Path | None = None) -> Path:
    """Export a human-friendly Markdown digest."""
    out = out or (EXPORT / "airdrop_digest.md")
    items = json.loads(SCORED.read_text(encoding="utf-8")).get("items", [])
    if not items:
        out.write_text("# Airdrop Intelligence\n\n_لا توجد بيانات حالياً_", encoding="utf-8")
        return out

    lines = [
        "# ⚡ Airdrop Intelligence — Digest",
        f"- **updated_at**: {json.loads(SCORED.read_text(encoding='utf-8')).get('updated_at','')}",
        f"- **total items**: {json.loads(SCORED.read_text(encoding='utf-8')).get('total','')}",
        f"- **Grade A**: {json.loads(SCORED.read_text(encoding='utf-8')).get('by_grade',{}).get('A','')}",
        f"- **scams blocked**: {json.loads(SCORED.read_text(encoding='utf-8')).get('scams_blocked','')}",
        "",
        "## 🟢 Grade A (top 15)",
        "",
    ]
    for it in sorted(items, key=lambda x: -x.get("score", 0))[:15]:
        lines += [
            f"### {it.get('score')} — {it.get('title','')}",
            f"- **source**: {it.get('source','')}",
            f"- **date**: {it.get('date','')}",
            f"- **signals**: {', '.join(it.get('signals', [])) or '—'}",
            f"- [رابط]({it.get('link','')})",
            "",
        ]
    out.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"✅ exported MD → {out}")
    return out


# ── GitHub Issues export (cloud bridge) ──────────────────────────────────
def export_github_issues(issues: list[str], repo: str = "esprieaether") -> dict:
    """
    Format airdrop intelligence as GitHub Issues suitable for the cloud
    bridge (PC poller reads them from the repo and posts to Telegram).
    Returns {'title', 'body', 'labels'}.
    """
    graded = json.loads(SCORED.read_text(encoding="utf-8"))
    top = sorted(graded.get("items", []), key=lambda x: -x.get("score", 0))[:10]
    lines = [
        "## ⚡ Airdrop Intelligence Digest",
        "",
        f"**updated_at**: {graded.get('updated_at','')}",
        f"**total**: {graded.get('total','')} · Grade A: {graded.get('by_grade',{}).get('A','')} · scams blocked: {graded.get('scams_blocked','')}",
        "",
        "### Top candidates",
        "",
    ]
    for it in top:
        lines += [
            f"• **[{it.get('grade','')} · {it.get('score')}]** {it.get('title','')[:80]}",
            f"  __{it.get('source','')}__ · {it.get('date','')}",
            "",
        ]
    return {
        "title": f"📡 Airdrop Intelligence Digest — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "body": "\n".join(lines),
        "labels": ["airdrop", "intelligence", "auto", "daily", "grade-a"],
    }


# ── Telegram notify ──────────────────────────────────────────────────────
def notify_telegram(chat_id: str, top_n: int = 8) -> str:
    """Build a Telegram message announcing new Grade A airdrops (for the cloud bridge to send)."""
    from airdrop_scorer import format_telegram
    from airdrop_agent import AirdropAgent
    agent = AirdropAgent()
    # recent new airdrops
    recent = agent.get_recent(10)
    top = top_candidates(top_n, min_grade="B")
    msg = format_telegram(top_n)
    if not recent and not top:
        return "📭 لا توجد فرص مؤهلة في هذه المرة."
    return msg or "⚠️ لم يتم التعلم — ملف scoring فارغ (" + str(len(recent)) + " new airdrops)"


# ── CLI ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("all", "json"):
        export_json()
    if cmd in ("all", "csv"):
        export_csv()
    if cmd in ("all", "md"):
        export_md()
    if cmd in ("all", "github"):
        export_github_issues([])
    if cmd in ("all", "notify"):
        print(notify_telegram("8980464794"))
    if cmd == "full":
        agent = AirdropAgent()
        from airdrop_agent import AirdropAgent
        raw = agent.fetch_all()
        scored = score_all(raw)
        print(f"✅ {len(raw)} fetched → {len(scored)} scored | A: {sum(1 for s in scored if s.grade=='A')}")
