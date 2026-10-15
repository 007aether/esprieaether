#!/usr/bin/env python3
"""
skill_harvester.py — turn the veille index into actionable skills/tasks

WHAT: Reads data/veille_index.json (500 repos, 25 categories), and for each
top repo with a README, extracts what it does + how it could serve
EsprieAether or Sunna, and writes:
  - data/skill_candidates.json — ranked list of "adopt this pattern" items
  - data/skill_digest.md — human/agent-readable summary

WHY: veille finds 500 repos; nobody reads 500 repos. This is the filter:
which of them are worth cloning, which are reference-only, and what concrete
task (if any) each one spawns for the mesh agents.

Pattern source: ARIS (Auto-Research-In-Sleep) — markdown-only skill
harvesting from the veille index.

Usage:
  python skill_harvester.py            # harvest candidates
  python skill_harvester.py --top 10   # show top 10
"""

import json
import logging
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_FILE = BASE_DIR / "data" / "veille_index.json"
CANDIDATES_FILE = BASE_DIR / "data" / "skill_candidates.json"
DIGEST_FILE = BASE_DIR / "data" / "skill_digest.md"

logger = logging.getLogger("skill_harvester")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

# which categories map to which stack need
CATEGORY_VALUE = {
    "ai_agent_framework": ("esprieaether", 30, "agent mesh / orchestrator pattern"),
    "self_evolving": ("esprieaether", 25, "autonomous_loop self-improvement"),
    "rag_memory": ("esprieaether", 25, "vector_memory_agent upgrade"),
    "local_llm": ("esprieaether", 25, "ollama/colibri alternatives"),
    "orchestration": ("esprieaether", 20, "durable task queue"),
    "observability": ("esprieaether", 20, "digest_agent / monitoring"),
    "cloud_free": ("esprieaether", 15, "github-as-vps extensions"),
    "crypto_airdrop": ("esprieaether", 15, "airdrop agent"),
    "security_edr": ("esprieaether", 15, "guardian agent"),
    "voice_interface": ("esprieaether", 15, "voice_agent"),
    "messaging_bridge": ("esprieaether", 10, "whatsapp/telegram bridges"),
    "metal_fabrication": ("sunna", 20, "workshop projects"),
    "cnc_laser_dxf": ("sunna", 20, "product manufacturing"),
    "gates_ironwork": ("sunna", 15, "catalogue expansion"),
    "steel_structures": ("sunna", 15, "catalogue expansion"),
    "farm_equipment": ("sunna", 15, "catalogue expansion"),
    "trailers_carts": ("sunna", 10, "catalogue expansion"),
    "estimating_costing": ("sunna", 20, "cost_estimator_agent"),
    "decor_signage": ("sunna", 10, "catalogue expansion"),
    "workshop_tools": ("sunna", 15, "cost_estimator_agent"),
    "galvanizing_coating": ("sunna", 15, "cost_estimator_agent"),
    "pipe_tube_work": ("sunna", 10, "catalogue expansion"),
    "brouettes": ("sunna", 10, "catalogue expansion"),
    "productivity": ("sunna", 10, "bilan_bot"),
    "telegram_bots": ("esprieaether", 10, "bot.py patterns"),
}


def load_index():
    if INDEX_FILE.exists():
        try:
            return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"repos": []}
    return {"repos": []}


def classify_repo(repo):
    """Decide: adopt (build it in), reference (read only), skip."""
    cat = repo.get("category", "")
    stars = repo.get("stars", 0)
    lang = repo.get("lang", "")
    desc = (repo.get("desc", "") or "").lower()
    name = repo.get("name", "")

    # skip: abandoned or irrelevant
    if repo.get("updated", "2000") < "2025-06-01":
        return "skip", "stale (>6 months)"

    # skip: pure content/dataset repos
    if any(k in desc for k in ("awesome list", "curated list", "cheat sheet", "interview questions", "roadmap")):
        return "skip", "content list"

    # adopt candidates: high stars + right language + active
    if stars >= 3000 and lang in ("Python", "TypeScript", "C", "C++", "Rust", "Go"):
        target, value, use = CATEGORY_VALUE.get(cat, ("esprieaether", 5, "general"))
        if stars >= 10000:
            return "adopt", f"{target}: {use}"
        return "reference", f"{target}: {use}"

    if stars >= 1000:
        return "reference", "review pattern"

    return "skip", "low signal"


def harvest(limit_per_category=3):
    """Harvest the top repos per category into candidates."""
    index = load_index()
    repos = index.get("repos", [])

    by_cat = {}
    for r in repos:
        by_cat.setdefault(r.get("category", "other"), []).append(r)

    candidates = []
    for cat, cat_repos in by_cat.items():
        for r in cat_repos[:limit_per_category]:
            decision, reason = classify_repo(r)
            target, value, use = CATEGORY_VALUE.get(cat, ("esprieaether", 5, "general"))
            candidates.append({
                "name": r["name"],
                "url": r["url"],
                "stars": r["stars"],
                "category": cat,
                "lang": r.get("lang", ""),
                "desc": (r.get("desc", "") or "")[:150],
                "decision": decision,
                "reason": reason,
                "target": target,
                "value": value,
            })

    # rank: value + stars
    import math
    for c in candidates:
        c["score"] = round(c["value"] + min(20, math.log10(max(c["stars"], 1)) * 3), 1)
    candidates.sort(key=lambda x: -x["score"])

    CANDIDATES_FILE.parent.mkdir(exist_ok=True)
    CANDIDATES_FILE.write_text(json.dumps({
        "updated": datetime.now(timezone.utc).isoformat(),
        "total": len(candidates),
        "adopt": sum(1 for c in candidates if c["decision"] == "adopt"),
        "reference": sum(1 for c in candidates if c["decision"] == "reference"),
        "candidates": candidates,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    # digest
    adopt = [c for c in candidates if c["decision"] == "adopt"]
    ref = [c for c in candidates if c["decision"] == "reference"]
    lines = [
        f"# 🎯 Skill Harvest — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        "",
        f"**{len(candidates)}** candidates from the veille index · "
        f"**{len(adopt)}** adopt · **{len(ref)}** reference",
        "",
        "## 🏗️ Adopt (build into the stack)",
        "",
    ]
    for c in adopt[:15]:
        lines.append(f"- [{c['stars']}★] [{c['name']}]({c['url']}) → *{c['reason']}*")
    lines += ["", "## 📖 Reference (read the pattern)", ""]
    for c in ref[:15]:
        lines.append(f"- [{c['stars']}★] [{c['name']}]({c['url']}) — {c['desc'][:70]}")
    DIGEST_FILE.write_text("\n".join(lines), encoding="utf-8")

    return candidates


def format_telegram(top=8):
    """Telegram digest of adopt candidates."""
    if not CANDIDATES_FILE.exists():
        return "📭 ما كاين حتى harvest — شغّل veille أولاً"
    data = json.loads(CANDIDATES_FILE.read_text(encoding="utf-8"))
    lines = [f"🎯 *Skill Harvest* — {data['total']} مرشح\n"]
    for c in data["candidates"][:top]:
        icon = "🏗️" if c["decision"] == "adopt" else "📖"
        lines.append(f"{icon} `{c['stars']}`★ {c['name']}")
        lines.append(f"   → {c['reason'][:60]}")
    return "\n".join(lines)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=0)
    ap.add_argument("--telegram", action="store_true")
    args = ap.parse_args()

    if args.telegram:
        print(format_telegram())
        return

    candidates = harvest()
    print(f"✅ {len(candidates)} candidates → {CANDIDATES_FILE}")
    adopt = [c for c in candidates if c["decision"] == "adopt"]
    print(f"   adopt: {len(adopt)} · reference: {len(candidates) - len(adopt)}")
    for c in candidates[:args.top or 10]:
        print(f"   {c['decision']:9s} [{c['stars']:>6}★] {c['name'][:40]} → {c['reason'][:50]}")


if __name__ == "__main__":
    main()
