#!/usr/bin/env python3
"""
airdrop_scraper.py — specialized airdrop scrapers

Augments the RSS-based agent with direct page scraping from
airdrop-specific platforms (airdrops.io, icodrops, coinmarketcap)
and GitHub trending/search — sources the RSS feeds don't cover.

Each scraper returns dicts with the same shape the scorer expects:
  {title, link, source, date}
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

UA = {"User-Agent": "Mozilla/5.0 (compatible; EsprieAether/1.0; +https://github.com/007aether/esprieaether)"}
TIMEOUT = 15
DB_PATH = Path(__file__).parent.parent / "data" / "airdrop_scraped.json"


# ── airdrops.io ──────────────────────────────────────────────────────
def scrape_airdrops_io(limit: int = 30) -> list:
    """Scrape airdrops.io listing page — project name, status, reward."""
    items = []
    try:
        r = requests.get("https://airdrops.io/", headers=UA, timeout=TIMEOUT)
        r.raise_for_status()
        html = r.text

        # airdrops.io renders project cards with <h2>/<h3> project names
        # plus data-* date attributes on each card
        skip = {"latest airdrops", "hottest airdrops", "crypto airdrops, verified daily since 2017",
                "home", "about", "contact", "advertise", "blog", "guides", "airdrop guide",
                "how to get airdrops", "what is an airdrop", "best airdrops", "upcoming airdrops"}

        headings = re.findall(r'<h[23][^>]*>([^<]{3,50})</h[23]>', html)
        seen = set()
        for h in headings:
            h = h.strip()
            if not h or h.lower() in skip or h.lower() in seen:
                continue
            seen.add(h.lower())
            slug = h.lower().replace(" ", "-").replace(".", "")
            items.append({
                "title": h,
                "link": f"https://airdrops.io/{slug}/",
                "source": "airdrops.io",
                "date": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"),
            })
            if len(items) >= limit:
                break
    except Exception as e:
        print(f"  ⚠ airdrops.io: {e}")
    return items


# ── icodrops ─────────────────────────────────────────────────────────
def scrape_icodrops(limit: int = 20) -> list:
    """Scrape icodrops active ICO/IDO list — project + interest score."""
    items = []
    try:
        r = requests.get("https://icodrops.com/", headers=UA, timeout=TIMEOUT)
        r.raise_for_status()
        html = r.text

        # icodrops uses a ticker with project names
        names = re.findall(r'<a[^>]*href="(https://icodrops\.com/[a-z0-9\-]+)"[^>]*>([^<]{3,50})</a>', html)
        seen = set()
        for href, name in names[:limit]:
            name = name.strip()
            if not name or name.lower() in seen:
                continue
            seen.add(name.lower())
            items.append({
                "title": name,
                "link": href,
                "source": "icodrops",
                "date": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"),
            })
    except Exception as e:
        print(f"  ⚠ icodrops: {e}")
    return items


# ── CoinMarketCap airdrops ───────────────────────────────────────────
def scrape_coinmarketcap(limit: int = 20) -> list:
    """Scrape CoinMarketCap airdrop listing."""
    items = []
    try:
        r = requests.get("https://coinmarketcap.com/airdrop/", headers=UA, timeout=TIMEOUT)
        r.raise_for_status()
        html = r.text

        # CMC renders airdrops in table rows with project names
        names = re.findall(
            r'<p[^>]*class="[^"]*sc-[^"]*"[^>]*>([A-Z][a-zA-Z0-9\s]{2,40})</p>',
            html
        )
        seen = set()
        for name in names[:limit]:
            name = name.strip()
            if not name or name.lower() in seen:
                continue
            seen.add(name.lower())
            slug = name.lower().replace(" ", "-")
            items.append({
                "title": name,
                "link": f"https://coinmarketcap.com/currencies/{slug}/",
                "source": "coinmarketcap",
                "date": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"),
            })
    except Exception as e:
        print(f"  ⚠ coinmarketcap: {e}")
    return items


# ── GitHub trending (crypto/web3 repos) ─────────────────────────────
def scrape_github_trending(limit: int = 15) -> list:
    """GitHub trending repos — proxy for active airdrop-farming projects."""
    items = []
    try:
        r = requests.get("https://github.com/trending", headers=UA, timeout=TIMEOUT)
        r.raise_for_status()
        html = r.text

        repos = re.findall(
            r'<h2[^>]*>\s*<a[^>]*href="(/[^/"]+/[^/"]+)"[^>]*>\s*(?:<[^>]+>\s*)*([^<]+)',
            html
        )
        seen = set()
        for path, name in repos[:limit]:
            name = name.strip()
            if not name or name.lower() in seen:
                continue
            seen.add(name.lower())
            items.append({
                "title": f"GitHub: {name}",
                "link": f"https://github.com{path}",
                "source": "github_trending",
                "date": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"),
            })
    except Exception as e:
        print(f"  ⚠ github trending: {e}")
    return items


# ── GitHub search (airdrop-related repos) ────────────────────────────
def scrape_github_search(limit: int = 15) -> list:
    """GitHub API search for airdrop/airdrop-farming repos."""
    items = []
    try:
        r = requests.get(
            "https://api.github.com/search/repositories",
            params={"q": "airdrop farming", "sort": "updated", "order": "desc", "per_page": limit},
            headers=UA, timeout=TIMEOUT
        )
        if r.status_code == 200:
            for repo in r.json().get("items", [])[:limit]:
                items.append({
                    "title": f"GitHub: {repo['full_name']}",
                    "link": repo["html_url"],
                    "source": "github_search",
                    "date": repo.get("updated_at", datetime.now(timezone.utc).isoformat()),
                })
    except Exception as e:
        print(f"  ⚠ github search: {e}")
    return items


# ── Orchestrator ─────────────────────────────────────────────────────
def scrape_all() -> list:
    """Run all specialized scrapers and persist the merged result."""
    all_items = []

    print("  📡 airdrops.io ...")
    a = scrape_airdrops_io()
    all_items.extend(a)
    print(f"    → {len(a)} items")

    print("  📡 icodrops ...")
    b = scrape_icodrops()
    all_items.extend(b)
    print(f"    → {len(b)} items")

    print("  📡 coinmarketcap ...")
    c = scrape_coinmarketcap()
    all_items.extend(c)
    print(f"    → {len(c)} items")

    print("  📡 github trending ...")
    d = scrape_github_trending()
    all_items.extend(d)
    print(f"    → {len(d)} items")

    print("  📡 github search ...")
    e = scrape_github_search()
    all_items.extend(e)
    print(f"    → {len(e)} items")

    DB_PATH.parent.mkdir(exist_ok=True)
    DB_PATH.write_text(json.dumps({
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "total": len(all_items),
        "items": all_items,
    }, ensure_ascii=False, indent=2))

    print(f"\n  ✅ total scraped: {len(all_items)}")
    return all_items


if __name__ == "__main__":
    print("═" * 60)
    print("🕷️  Airdrop Scraper — specialized sources")
    print("═" * 60)
    scrape_all()
