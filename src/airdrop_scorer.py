#!/usr/bin/env python3
"""
airdrop_scorer.py — EsprieAether Airdrop Intelligence

Turns raw airdrop news into a ranked, risk-screened opportunity list.

Scoring model (0-100):
  +25  project has real GitHub activity (repo public, commits recent)
  +20  no token yet (pre-launch = higher upside)
  +15  backed by known investors / audit firm
  +10  testnet-only requirement (cheap to participate)
  +10  mainnet live but no token announced
  -50  scam keywords detected (seed phrase, wallet connect, guaranteed)
  -30  no GitHub / no audit / anonymous team
  -20  pay-to-play (requires buying tokens to qualify)

The score is a triage signal, NOT advice. Every candidate still
requires manual review before any wallet touches it.
"""

import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "airdrop_scored.json"

# ── Signal dictionaries ──────────────────────────────────────────────
SCAM_PATTERNS = [
    r"seed\s*phrase", r"private\s*key", r"connect\s*wallet\s*to\s*claim",
    r"guaranteed\s*(airdrop|profit|reward)", r"send\s*\d+\s*(eth|usdt|bnb)",
    r"limited\s*slots?\s*claim\s*now", r"instant\s*payout", r"\bairdrop\s*generator\b",
]

SAFE_SIGNALS = {
    "audit": [r"audit(ed)?\s+by", r"trail\s*of\s*bits", r"openzeppelin", r"certik", r"halborn", r"spearbit"],
    "vc": [r"led\s+by", r"raised\s+\$", r"series\s+[a-c]\b", r"investors?\s+include", r"a16z", r"paradigm", r"polychain", r"sequoia", r"binance\s+labs"],
    "testnet": [r"testnet", r"faucet", r"devnet", r"goerli", r"sepolia", r"holesky"],
    "mainnet_live": [r"mainnet\s+(is\s+)?live", r"live\s+on\s+mainnet", r"mainnet\s+launch"],
    "no_token": [r"no\s+token\s+yet", r"token\s+tbd", r"no\s+token\s+announced", r"pre[-\s]?token"],
    "pay_to_play": [r"buy\s+\$?\d+\s+to\s+qualify", r"stake\s+to\s+earn", r"purchase\s+required", r"minimum\s+deposit"],
}

GRADE_BANDS = [
    (80, "A", "strong candidate — review in depth"),
    (65, "B", "worth a closer look"),
    (50, "C", "monitor only"),
    (0,  "D", "skip — weak or risky"),
]


@dataclass
class ScoredAirdrop:
    title: str
    link: str
    source: str
    date: str
    score: int = 0
    grade: str = "D"
    signals: list = field(default_factory=list)
    flags: list = field(default_factory=list)
    has_github: bool = False
    pay_to_play: bool = False
    scored_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _find(text: str, patterns: list) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def enrich_item(item: dict, timeout: int = 10) -> dict:
    """Fetch the airdrop page and extract a body snippet for deeper scoring."""
    link = item.get("link", "")
    if not link.startswith("http"):
        return item
    try:
        import requests
        r = requests.get(link, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (compatible; EsprieAether/1.0)"
        })
        r.raise_for_status()
        # crude text extraction — strip tags
        text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", r.text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        item["body"] = text[:4000]
        # detect github link inside the page
        if "github.com" in r.text and not item.get("has_github"):
            item["has_github"] = True
    except Exception:
        pass
    return item


def score_airdrop(item: dict) -> ScoredAirdrop:
    """Score one airdrop record. Deterministic after enrichment."""
    body = item.get("body", "")
    text = f"{item.get('title', '')} {item.get('link', '')} {body}"
    scored = ScoredAirdrop(
        title=item.get("title", "untitled"),
        link=item.get("link", ""),
        source=item.get("source", ""),
        date=item.get("date", ""),
    )

    # ── Hard scam filter ──
    if _find(text, SCAM_PATTERNS):
        scored.flags.append("SCAM_PATTERN")
        scored.score = max(0, scored.score - 50)

    # ── airdrops.io project page = real opportunity ──
    if "airdrops.io" in scored.link and not item.get("has_github"):
        scored.score += 30
        scored.signals.append("airdrops_io_listed")
        # claim live = confirmed airdrop
        if _find(body, [r"claim\s+live", r"claim\s+now", r"eligible", r"step-by-step"]):
            scored.score += 20
            scored.signals.append("claim_live")
        # potential/confirmed airdrop mention
        if _find(body, [r"potential\s+airdrop", r"how\s+to\s+be\s+eligible", r"confirmed\s+airdrop"]):
            scored.score += 15
            scored.signals.append("potential_airdrop")
        # confirmed airdrop = highest confidence
        if _find(body, [r"airdrop\s+confirmed", r"airdrop\s+is\s+confirmed", r"tge\s+for"]):
            scored.score += 15
            scored.signals.append("confirmed_airdrop")
        # waitlisted = demand signal
        if _find(body, [r"wallets\s+waitlisted", r"waitlist", r"\d+K\s+users"]):
            scored.score += 10
            scored.signals.append("waitlisted")
        # no token yet = higher upside
        if _find(body, [r"no\s+token\s+yet", r"token\s+tbd", r"pre[-\s]?token", r"airdrop\s+is\s+live"]):
            scored.score += 10
            scored.signals.append("pre_token")

    # ── Positive signals ──
    if _find(text, SAFE_SIGNALS["audit"]):
        scored.score += 15
        scored.signals.append("audited")
    if _find(text, SAFE_SIGNALS["vc"]):
        scored.score += 15
        scored.signals.append("vc_backed")
    if _find(text, SAFE_SIGNALS["testnet"]):
        scored.score += 10
        scored.signals.append("testnet")
    if _find(text, SAFE_SIGNALS["mainnet_live"]):
        scored.score += 5
        scored.signals.append("mainnet_live")
    if _find(text, SAFE_SIGNALS["no_token"]):
        scored.score += 20
        scored.signals.append("no_token_yet")

    # ── GitHub repo signal (only for airdrop-related repos) ──
    if "github.com" in text or item.get("has_github"):
        scored.has_github = True
        if _find(text, [r"airdrop", r"crypto", r"web3", r"blockchain", r"defi", r"token", r"tge", r"points"]):
            scored.score += 25
            scored.signals.append("has_github")
        else:
            scored.signals.append("generic_repo")

    # ── Negative signals ──
    if _find(text, SAFE_SIGNALS["pay_to_play"]):
        scored.score = max(0, scored.score - 20)
        scored.pay_to_play = True
        scored.flags.append("pay_to_play")
    if not scored.has_github and "airdrops.io" not in scored.link:
        scored.score = max(0, scored.score - 10)
        scored.flags.append("no_github")

    # ── Freshness bonus (last 7 days) ──
    try:
        from email.utils import parsedate_to_datetime
        pub = parsedate_to_datetime(scored.date)
        age_days = (datetime.now(timezone.utc) - pub).days
        if age_days <= 7:
            scored.score += 10
            scored.signals.append("fresh")
    except Exception:
        pass

    scored.score = max(0, min(100, scored.score))
    for threshold, grade, _ in GRADE_BANDS:
        if scored.score >= threshold:
            scored.grade = grade
            break

    return scored


def score_all(items: list, enrich: bool = True, enrich_limit: int = 25, deep_enrich: bool = False) -> list:
    """Score a batch and persist the ranked result.

    Enrichment (page fetch) is limited to the top N by raw recency to keep
    the run fast; the rest are scored on title+URL only.
    deep_enrich=True also fetches airdrops.io project pages + GitHub stats.
    """
    if enrich:
        # enrich the freshest 25 (parsedate may fail; fallback = first N)
        def _age(it):
            try:
                from email.utils import parsedate_to_datetime
                return (datetime.now(timezone.utc) - parsedate_to_datetime(it.get("date", ""))).days
            except Exception:
                return 9999
        candidates = sorted(items, key=_age)[:enrich_limit]
        for it in candidates:
            enrich_item(it)

    if deep_enrich:
        try:
            from airdrop_enricher import enrich_batch, enrich_airdrops_io, enrich_github
            for it in items:
                link = it.get("link", "")
                # airdrops.io project page
                if "airdrops.io" in link and not it.get("has_github"):
                    extra = enrich_airdrops_io(link)
                    it["body"] = (it.get("body", "") + " " + extra.get("description", "") + " " + extra.get("body", "")).strip()
                    if extra.get("github"):
                        it["has_github"] = True
                        it["github_url"] = extra["github"]
                        it["body"] += " github.com " + extra["github"]
                # GitHub repo stats
                if "github.com" in link:
                    stats = enrich_github(link)
                    it["github_stats"] = stats
                    if stats.get("description"):
                        it["body"] = (it.get("body", "") + " " + stats["description"]).strip()
                    if stats.get("stars", 0) > 100:
                        it["body"] += " popular repo"
        except Exception as e:
            print(f"  ⚠ deep enrich: {e}")

    scored = [score_airdrop(i) for i in items]
    scored.sort(key=lambda s: s.score, reverse=True)

    DB_PATH.parent.mkdir(exist_ok=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(scored),
        "by_grade": {
            g: sum(1 for s in scored if s.grade == g)
            for g in ("A", "B", "C", "D")
        },
        "scams_blocked": sum(1 for s in scored if "SCAM_PATTERN" in s.flags),
        "items": [asdict(s) for s in scored],
    }
    DB_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return scored


def top_candidates(limit: int = 10, min_grade: str = "B") -> list:
    """Return the best candidates from the last scoring run."""
    if not DB_PATH.exists():
        return []
    data = json.loads(DB_PATH.read_text())
    order = {"A": 0, "B": 1, "C": 2, "D": 3}
    floor = order.get(min_grade, 1)
    ranked = sorted(data["items"], key=lambda s: order.get(s["grade"], 3))
    return [s for s in ranked if order.get(s["grade"], 3) <= floor][:limit]


def format_telegram(limit: int = 5) -> str:
    """Telegram digest of the top scored airdrops."""
    cands = top_candidates(limit, min_grade="B")
    if not cands:
        return "📭 لا توجد فرص مؤهلة حالياً (لا شيء فوق الدرجة B)"

    lines = [f"🎯 *أفضل فرص Airdrop* ({len(cands)} مؤهلة)\n"]
    for i, s in enumerate(cands, 1):
        grade = s["grade"]
        badge = {"A": "🟢", "B": "🔵", "C": "🟡", "D": "🔴"}.get(grade, "⚪")
        sig = ", ".join(s["signals"][:3]) or "—"
        lines.append(f"{badge} *[{grade} · {s['score']}]* {s['title'][:60]}")
        lines.append(f"    `{sig}`")
        lines.append(f"    [رابط]({s['link']})\n")
    return "\n".join(lines)


if __name__ == "__main__":
    print("═" * 60)
    print("🎯 Airdrop Scorer — self test")
    print("═" * 60)

    from airdrop_agent import AirdropAgent
    agent = AirdropAgent()
    raw = agent.fetch_all()
    print(f"\n📥 fetched {len(raw)} raw items")

    scored = score_all(raw)
    print(f"🎯 scored {len(scored)} items")
    print(f"   A: {sum(1 for s in scored if s.grade=='A')}"
          f"  B: {sum(1 for s in scored if s.grade=='B')}"
          f"  C: {sum(1 for s in scored if s.grade=='C')}"
          f"  D: {sum(1 for s in scored if s.grade=='D')}")
    print(f"   🚫 scams blocked: {sum(1 for s in scored if 'SCAM_PATTERN' in s.flags)}")

    print("\n" + format_telegram(5))
