#!/usr/bin/env python3
"""
veille_agent.py — Unified 24/7 tech watch: GitHub + trending → EsprieAether + Sunna

WHAT: One agent that watches GitHub across 25 categories (EsprieAether's own
evolution topics + Sunna's metal-fabrication topics), harvesting up to 500
repos per run, scoring them by relevance to our stack, and writing a digest.
Replaces the separate github_evolve (5 queries) + Sunna veille_bot (11 cats)
with ONE searchable index both workspaces read.

WHY: github_evolve pointed at the dead `~/AETHER_V8` path and ran 5 queries;
veille_bot ran 11 categories but wrote only to the Sunna workspace. This
merges both, fixes the path bug, and feeds the agent mesh + autonomous loop.

OUTPUTS:
  data/veille_index.json      — all harvested repos (deduped by URL, capped 500)
  data/veille_digest.md       — human/agent-readable top picks per category
"""

import json
import logging
import os
import sys
import time
import urllib.request
import urllib.parse
import urllib.error
import socket
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env", override=True)
except ImportError:
    pass

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
INDEX_FILE = BASE_DIR / "data" / "veille_index.json"
DIGEST_FILE = BASE_DIR / "data" / "veille_digest.md"

logger = logging.getLogger("veille_agent")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")

GITHUB_API = "https://api.github.com/search/repositories"

# ── 25 categories: EsprieAether evolution (12) + Sunna metal work (13) ──
CATEGORIES = {
    # EsprieAether stack
    "ai_agent_framework": ["ai agent framework python", "autonomous agent llm", "multi-agent orchestration"],
    "local_llm": ["ollama alternative", "local llm inference engine", "llama.cpp alternative", "gguf tools"],
    "telegram_bots": ["telegram bot python framework", "telegram automation python"],
    "self_evolving": ["self-improving agent", "self-evolving codebase", "auto-code-review agent"],
    "orchestration": ["task queue python", "durable workflow engine", "job scheduler python"],
    "observability": ["self-hosted monitoring", "uptime monitoring self-hosted", "log analysis agent"],
    "cloud_free": ["github actions automation", "free serverless compute", "edge functions self-hosted"],
    "crypto_airdrop": ["airdrop farming automation", "crypto wallet monitor", "web3 python tools"],
    "security_edr": ["open source edr", "host intrusion detection", "yara rules"],
    "rag_memory": ["local rag vector database", "embeddings sqlite", "knowledge graph tool"],
    "voice_interface": ["speech to text local", "whisper alternative python", "voice assistant local"],
    "messaging_bridge": ["whatsapp bridge api", "signal bot python", "matrix bridge"],

    # Sunna metal fabrication
    "metal_fabrication": ["metal fabrication projects", "welding projects diy", "sheet metal tools"],
    "cnc_laser_dxf": ["laser cut dxf", "cnc plasma dxf", "cnc router plans"],
    "gates_ironwork": ["wrought iron gate", "metal gate design", "portail fer forge"],
    "steel_structures": ["steel structure design", "charpente metallique", "steel frame calculator"],
    "farm_equipment": ["livestock feeder design", "abreuvoir betail", "cattle equipment metal"],
    "trailers_carts": ["trailer plans diy", "remorque plans", "utility trailer build"],
    "galvanizing_coating": ["galvanizing process", "powder coating diy", "zinc coating"],
    "workshop_tools": ["weld calculator", "cut list optimizer", "sheet metal nesting"],
    "decor_signage": ["metal decor laser cut", "signage dxf", "garden sculpture plans"],
    "estimating_costing": ["manufacturing cost calculator", "devis generator", "invoice generator python"],
    "pipe_tube_work": ["pipe bending jig", "tube notcher plans", "scaffold design"],
    "brouettes": ["wheelbarrow plans", "brouette metallique", "hand cart build"],
    "productivity": ["shop management software", "manufacturing productivity", "small business inventory"],
}

# relevance keywords → score boost when found in repo name/description/topics
RELEVANCE = {
    "esprieaether": ["ai", "agent", "llm", "telegram", "ollama", "autonomous", "self-host", "automation"],
    "sunna": ["metal", "steel", "weld", "cnc", "dxf", "galvan", "fabrication", "gate", "trailer", "forge"],
}


def _headers():
    h = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "esprieaether-veille/1.0",
    }
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def gh_search(query, limit=20, sort="stars"):
    """One GitHub search call. Returns list of repo dicts."""
    params = urllib.parse.urlencode({
        "q": query, "sort": sort, "order": "desc", "per_page": min(limit, 100),
    })
    url = f"{GITHUB_API}?{params}"
    try:
        req = urllib.request.Request(url, headers=_headers())
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            try:
                return json.loads(data.decode('utf-8'))
            except UnicodeDecodeError:
                return json.loads(data.decode('latin-1'))
    except urllib.error.HTTPError as e:
        logger.error(f"❌ GitHub API {e.code}: {query}")
        return []
    except urllib.error.URLError as e:
        if isinstance(e.reason, socket.timeout):
            logger.warning(f"⏱️ {query}: وقت استجابة متوقف")
        elif isinstance(e.reason, ConnectionResetError):
            logger.warning(f"🔌 {query}: قطع الاتصال")
        else:
            logger.warning(f"⚠️ {query}: {e.reason}")
        return []
    except Exception as e:
        logger.warning(f"⚠️ بحث '{query}': {type(e).__name__}: {e}")
        return []
    req = urllib.request.Request(f"{GITHUB_API}?{params}", headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code in (403, 429):
            logger.warning(f"  rate limited on '{query}' — waiting 60s")
            time.sleep(60)
            return []
        logger.warning(f"  HTTP {e.code} on '{query}'")
        return []
    except Exception as e:
        logger.warning(f"  search error '{query}': {e}")
        return []

    repos = []
    for item in data.get("items", [])[:limit]:
        repos.append({
            "name": item["full_name"],
            "url": item["html_url"],
            "stars": item["stargazers_count"],
            "lang": item.get("language") or "",
            "desc": (item.get("description") or "")[:200],
            "topics": item.get("topics", [])[:8],
            "updated": item.get("updated_at", "")[:10],
            "forks": item.get("forks_count", 0),
        })
    return repos


def score_repo(repo, target="esprieaether"):
    """0-100 relevance: stars (log) + freshness + keyword hits."""
    import math
    kws = RELEVANCE.get(target, RELEVANCE["esprieaether"])
    text = (repo["name"] + " " + repo["desc"] + " " + " ".join(repo["topics"])).lower()
    hits = sum(1 for k in kws if k in text)
    star_score = min(30, math.log10(max(repo["stars"], 1)) * 6)
    kw_score = min(40, hits * 10)
    fresh_score = 15 if repo["updated"] >= "2026-01-01" else 5
    lang_score = 15 if repo["lang"] in ("Python", "C", "C++", "TypeScript", "Rust", "Go") else 5
    return round(star_score + kw_score + fresh_score + lang_score)


def harvest(categories=None, per_query=20, target="esprieaether", delay=2):
    """Harvest all categories. Returns (index, digest_dict)."""
    cats = categories or list(CATEGORIES.keys())
    all_repos = {}

    for cat in cats:
        queries = CATEGORIES.get(cat, [])
        found = []
        for q in queries:
            repos = gh_search(q, limit=per_query)
            for r in repos:
                r["category"] = cat
                r["query"] = q
                r["score"] = score_repo(r, target)
                found.append(r)
            time.sleep(delay)  # GitHub search: 10 req/min unauthenticated
        # dedupe within category by URL, keep highest score
        by_url = {}
        for r in found:
            if r["url"] not in by_url or r["score"] > by_url[r["url"]]["score"]:
                by_url[r["url"]] = r
        all_repos[cat] = sorted(by_url.values(), key=lambda x: -x["score"])
        logger.info(f"  {cat}: {len(all_repos[cat])} repos")

    return all_repos


def save_index(index):
    """Merge with existing index, dedupe globally, cap at 500."""
    existing = []
    if INDEX_FILE.exists():
        try:
            existing = json.loads(INDEX_FILE.read_text(encoding="utf-8")).get("repos", [])
        except Exception:
            existing = []

    seen = {}
    for cat, repos in index.items():
        for r in repos:
            if r["url"] not in seen or r["score"] > seen[r["url"]]["score"]:
                seen[r["url"]] = r
    for r in existing:
        if r["url"] not in seen:
            seen[r["url"]] = r

    repos = sorted(seen.values(), key=lambda x: -x["score"])[:500]
    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "total": len(repos),
        "categories": {c: sum(1 for r in repos if r.get("category") == c) for c in CATEGORIES},
        "repos": repos,
    }
    INDEX_FILE.parent.mkdir(exist_ok=True)
    INDEX_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return payload


def write_digest(payload, top_n=5):
    """Markdown digest: top N per category + global top 10."""
    lines = [
        f"# 📡 Veille Digest — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        "",
        f"**{payload['total']} repos** across {len(payload['categories'])} categories.",
        "",
    ]
    repos = payload["repos"]
    for cat in CATEGORIES:
        cat_repos = [r for r in repos if r.get("category") == cat][:top_n]
        if not cat_repos:
            continue
        lines.append(f"## {cat}")
        for r in cat_repos:
            lines.append(f"- [{r['stars']}★] [{r['name']}]({r['url']}) — {r['desc'][:90]}")
        lines.append("")
    lines.append("## 🏆 Global Top 10")
    for r in repos[:10]:
        lines.append(f"- [{r['stars']}★] [{r['name']}]({r['url']}) ({r.get('category','')}) — {r['desc'][:80]}")
    DIGEST_FILE.parent.mkdir(exist_ok=True)
    DIGEST_FILE.write_text("\n".join(lines), encoding="utf-8")
    return str(DIGEST_FILE)


def format_telegram(top=10):
    """Compact Telegram digest."""
    if not INDEX_FILE.exists():
        return "📭 ما كاين حتى veille بعد. صيّف /veille"
    payload = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    lines = [f"📡 *Veille* — {payload['total']} repos ({payload['updated'][:10]})\n"]
    for r in payload["repos"][:top]:
        lines.append(f"`{r['stars']}`★ {r['name']}")
        lines.append(f"   {r['desc'][:70]}")
    return "\n".join(lines)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="one harvest cycle")
    ap.add_argument("--categories", nargs="*", default=None)
    ap.add_argument("--target", default="esprieaether", choices=["esprieaether", "sunna"])
    ap.add_argument("--per-query", type=int, default=20)
    ap.add_argument("--telegram", action="store_true")
    args = ap.parse_args()

    if args.telegram:
        print(format_telegram())
        return

    logger.info(f"📡 veille harvest — target={args.target}, cats={len(args.categories or CATEGORIES)}")
    index = harvest(categories=args.categories, per_query=args.per_query, target=args.target)
    total = sum(len(v) for v in index.values())
    payload = save_index(index)
    digest = write_digest(payload)
    logger.info(f"✅ {total} harvested, {payload['total']} in index → {digest}")


if __name__ == "__main__":
    main()
