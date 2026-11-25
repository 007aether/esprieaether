#!/usr/bin/env python3
"""
airdrop_enricher.py — deep enrichment for airdrop opportunities

Takes the scraped airdrop list (names + links) and fetches each project
page to extract:
  - description (what the project does)
  - GitHub repo (if any)
  - Twitter/X handle
  - audit / VC signals
  - testnet vs mainnet status
  - reward amount (if stated)

This is the step that turns D-grade names into real A/B candidates.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

UA = {"User-Agent": "Mozilla/5.0 (compatible; EsprieAether/1.0; +https://github.com/007aether/esprieaether)"}
TIMEOUT = 20
ENRICHED_DB = Path(__file__).parent.parent / "data" / "airdrop_enriched.json"


def _extract_text(html: str) -> str:
    """Strip tags/scripts/styles → readable text."""
    text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<noscript[\s\S]*?</noscript>", " ", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def enrich_airdrops_io(url: str) -> dict:
    """Enrich one airdrops.io project page."""
    out = {"github": None, "twitter": None, "description": "", "reward": "", "status": "", "body": ""}
    try:
        r = requests.get(url, headers=UA, timeout=TIMEOUT)
        r.raise_for_status()
        html = r.text
        text = _extract_text(html)

        # GitHub link
        gh = re.findall(r"https?://github\.com/([A-Za-z0-9\-_]+/[A-Za-z0-9\-_.]+)", html)
        if gh:
            out["github"] = f"https://github.com/{gh[0]}"

        # Twitter/X
        tw = re.findall(r"https?://(?:twitter|x)\.com/([A-Za-z0-9_]{2,15})", html)
        tw = [t for t in tw if t.lower() not in ("airdrops_io", "airdropsio", "intent", "share", "home")]
        if tw:
            out["twitter"] = f"https://x.com/{tw[0]}"

        # Description — meta description is the cleanest signal
        meta = re.findall(r'<meta name="description" content="([^"]+)"', html)
        if meta:
            out["description"] = meta[0][:300]

        # Body text for deeper scoring (claim live, confirmed, etc.)
        out["body"] = text[:3000]

        # Reward hints
        rew = re.findall(r"(?:reward|airdrop|worth|value|est\.?\s*\$?[\d,]+)", text, re.IGNORECASE)
        if rew:
            out["reward"] = rew[0] if rew else ""

        # Status: claim live vs upcoming
        if re.search(r"claim\s+live", text, re.IGNORECASE):
            out["status"] = "claim_live"
        elif re.search(r"upcoming|potential|confirm", text, re.IGNORECASE):
            out["status"] = "upcoming"

    except Exception as e:
        out["error"] = str(e)[:100]
    return out


def enrich_github(repo_url: str) -> dict:
    """Enrich a GitHub repo via API — stars, forks, description, activity."""
    out = {"stars": 0, "forks": 0, "description": "", "language": "", "updated": "", "topics": []}
    try:
        api = repo_url.replace("github.com/", "api.github.com/repos/")
        r = requests.get(api, headers=UA, timeout=TIMEOUT)
        if r.status_code == 200:
            d = r.json()
            out["stars"] = d.get("stargazers_count", 0)
            out["forks"] = d.get("forks_count", 0)
            out["description"] = (d.get("description") or "")[:200]
            out["language"] = d.get("language") or ""
            out["updated"] = d.get("updated_at", "")
            out["topics"] = d.get("topics", [])[:5]
    except Exception as e:
        out["error"] = str(e)[:100]
    return out


def enrich_batch(items: list, limit: int = 30) -> list:
    """Enrich top N scored items. Saves to data/airdrop_enriched.json."""
    # normalise: accept ScoredAirdrop objects or dicts
    def _get(item, key, default=""):
        if isinstance(item, dict):
            return item.get(key, default)
        return getattr(item, key, default)

    enriched = []
    for i, item in enumerate(items[:limit]):
        title = _get(item, "title")
        link = _get(item, "link")
        has_github = _get(item, "has_github", False)

        rec = {
            "title": title,
            "link": link,
            "source": _get(item, "source"),
            "base_score": _get(item, "score", 0),
            "base_grade": _get(item, "grade", "D"),
        }

        # airdrops.io project page
        if "airdrops.io" in link and not has_github:
            rec.update(enrich_airdrops_io(link))

        # GitHub repo
        if "github.com" in link:
            rec["github_stats"] = enrich_github(link)

        enriched.append(rec)
        print(f"  [{i+1}/{min(limit, len(items))}] {title[:40]}")

    ENRICHED_DB.parent.mkdir(exist_ok=True)
    ENRICHED_DB.write_text(json.dumps({
        "enriched_at": datetime.now(timezone.utc).isoformat(),
        "total": len(enriched),
        "items": enriched,
    }, ensure_ascii=False, indent=2))
    return enriched


if __name__ == "__main__":
    print("═" * 60)
    print("🔬 Airdrop Enricher — deep page analysis")
    print("═" * 60)

    # Load scored items
    from airdrop_scorer import score_all
    from airdrop_scraper import scrape_all
    from airdrop_agent import AirdropAgent

    agent = AirdropAgent()
    rss = agent.fetch_all()
    scraped = scrape_all()
    combined = rss + scraped

    scored = score_all(combined, enrich=False)
    print(f"\n📊 scored {len(scored)} items, enriching top 30 ...")

    enriched = enrich_batch(scored, limit=30)
    print(f"\n✅ enriched {len(enriched)} items → data/airdrop_enriched.json")
