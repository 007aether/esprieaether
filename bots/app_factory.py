#!/usr/bin/env python3
"""
app_factory.py — EsprieAether's APP FACTORY: idea → score → MVP → code

WHAT: The user asked for an autonomous pipeline that turns ideas into real,
sellable mobile apps. This module IS that pipeline, living inside EsprieAether:

    STAGE 1  ideate   → generate 60 app ideas (router = llm7/colibri)
    STAGE 2  score    → rank on demand/monetization/effort/complexity (0-100)
    STAGE 3  select   → keep the best 20
    STAGE 4  mvp      → write a 1-page MVP spec (screens, data model, monetization)
    STAGE 5  code     → generate Expo/React Native + RevenueCat starter code
    STAGE 6  package  → copy-ready bundle per app under AppFactory/apps/<slug>/

WHY it lives here (not Replit): the user wants EsprieAether + JARVIS to OWN this
end-to-end. Replit is only the final paste+run step. Everything before (idea,
score, MVP, code) is generated and versioned here so it's reviewable, re-runnable,
and can be improved by the mesh agents (jarvis_dev writes more, self_improve fixes).

MONETIZATION (RevenueCat): every MVP ships with a paywall screen + RevenueCat
offerings scaffolding + a products config the user pastes into revenuecat.com.

SAFETY: generated code is staged (not auto-run). Real payments/App Store/Play
submission are human steps. No store credentials are ever stored here.

Usage:
    python app_factory.py ideate              # stage 1-3: 60 ideas → top 20
    python app_factory.py mvp --slug <slug>   # stage 4: MVP spec for one app
    python app_factory.py code --slug <slug>  # stage 5-6: Expo code + RevenueCat
    python app_factory.py status              # pipeline state
"""

import json
import logging
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FACTORY_DIR = BASE_DIR / "AppFactory"
IDEAS_FILE = FACTORY_DIR / "ideas.json"
TOP_FILE = FACTORY_DIR / "top20.json"
APPS_DIR = FACTORY_DIR / "apps"
LOG_FILE = FACTORY_DIR / "factory_log.json"

ROUTER_URL = "http://127.0.0.1:11435"
N_IDEAS = 60
TOP_N = 20

logger = logging.getLogger("app_factory")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "data" / "logs" / "app_factory.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


# ── router call ──────────────────────────────────────────────────────
def ask_router(prompt, system=None, max_tokens=3000, timeout=120):
    system = system or (
        "You are a senior mobile product strategist + React Native engineer. "
        "Respond with concrete, structured content. When asked for JSON, respond "
        "with ONLY valid JSON, no markdown fences."
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    # WHY aether-local first, cloud fallback: llm7 free tier exhausts daily
    # (500K tokens → 429 "retry after 61788s" = 17h). aether-local (colibri→
    # cherry→ollama) keeps working on the local 3B brain. aether-cloud is the
    # fallback when llm7 quota has reset.
    for model in ("aether-local", "aether-cloud"):
        try:
            data = json.dumps({
                "model": model, "messages": messages,
                "max_tokens": max_tokens, "temperature": 0.8,
            }).encode()
            req = urllib.request.Request(f"{ROUTER_URL}/v1/chat/completions", data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                result = json.loads(r.read().decode())
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"router {model} failed: {e} — trying next")
            continue
    logger.error("all router chains failed")
    return None


# ── STAGE 1: ideate ──────────────────────────────────────────────────
# WHY batched: a single 60-idea request (~4000 tokens) 502s or exhausts llm7's
# daily quota. We ask for BATCH_SIZE ideas per call, N_BATCHES times, with a
# short sleep between calls. aether-local (ollama 3B) has no daily quota.
BATCH_SIZE = 8
N_BATCHES = 8  # 8 × 8 = 64 (dedupe → ~60)
BATCH_SLEEP = 8  # seconds between batches (ollama-local, no llm7 quota)

IDEATE_PROMPT = """Give me {n} SHORT mobile app ideas (batch {b} of {nb}, pick DIFFERENT
categories/angles than a generic list). Each idea must be:
- in HIGH demand (people pay for this category)
- monetizable via subscription (a clear pro feature)
- buildable as an MVP by a solo dev in 1-2 weeks (React Native / Expo)
- a sharp niche wedge, NOT a generic clone

Keep each pitch under 15 words. Respond with ONLY a JSON array (no prose, no fences):
[
  {{"name": "App Name", "slug": "app-name", "category": "productivity",
    "pitch": "one sentence, what it does and for whom",
    "monetization": "the pro feature people pay for",
    "audience": "who pays"}}
]
Exactly {n} entries."""


def ideate(n=N_IDEAS):
    """Generate n app ideas via batched router calls (llm7-free-tier safe)."""
    import time
    all_ideas = []
    batches = max(1, (n + BATCH_SIZE - 1) // BATCH_SIZE)
    for b in range(1, batches + 1):
        logger.info(f"💡 batch {b}/{batches} ({BATCH_SIZE} ideas)...")
        raw = ask_router(IDEATE_PROMPT.format(n=BATCH_SIZE, b=b, nb=batches),
                         max_tokens=1400, timeout=180)
        if not raw:
            logger.warning(f"batch {b} failed — skipping")
            continue
        parsed = _parse_ideas(raw)
        all_ideas.extend(parsed)
        logger.info(f"  batch {b}: +{len(parsed)} (total {len(all_ideas)})")
        if b < batches:
            time.sleep(BATCH_SLEEP)  # let free-tier quota/rate-limit recover
    logger.info(f"✅ generated {len(all_ideas)} ideas total")
    return all_ideas


def _parse_ideas(raw):
    """Extract + normalize idea objects from router output."""
    raw = raw.strip()
    raw = re.sub(r"^```(json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if not m:
        return []
    try:
        ideas = json.loads(m.group(0))
    except Exception:
        return []
    out = []
    for idea in ideas:
        if not isinstance(idea, dict) or not idea.get("name"):
            continue
        slug = idea.get("slug") or idea.get("name", "")
        idea["slug"] = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")
        out.append(idea)
    return out


# ── STAGE 2: score ───────────────────────────────────────────────────
def score_idea(idea):
    """
    Heuristic score 0-100. Combines:
      - monetization strength (subscription keywords, clear pro feature)
      - demand signals (category popularity)
      - effort (MVP buildable fast = higher)
      - specificity (concrete pitch = higher, generic = lower)
    Router-scored ideas get a boost; this is the deterministic fallback.
    """
    text = (idea.get("pitch", "") + " " + idea.get("monetization", "") + " " +
            idea.get("name", "") + " " + idea.get("audience", "")).lower()

    # monetization (0-35)
    monet = 0
    if any(w in text for w in ("subscription", "pro", "premium", "unlock", "paywall", "subscribe")):
        monet += 20
    if any(w in text for w in ("monthly", "yearly", "tier", "plan")):
        monet += 10
    if any(w in text for w in ("b2b", "business", "team", "professional", "freelanc")):
        monet += 5  # B2B pays more

    # demand (0-30) — category weights
    cat = idea.get("category", "").lower()
    demand_map = {
        "productivity": 25, "finance": 25, "health": 22, "fitness": 22,
        "education": 20, "language": 20, "ai": 22, "creator": 20,
        "b2b": 20, "habit": 18, "food": 16, "travel": 16,
        "sleep": 18, "focus": 20, "note": 18, "relationship": 15,
    }
    demand = demand_map.get(cat, 15)

    # effort/buildability (0-20) — solo 1-2 week MVP = high
    effort = 15
    if any(w in text for w in ("simple", "tracker", "reminder", "log", "journal", "list")):
        effort += 5
    if any(w in text for w in ("realtime", "multiplayer", "social network", "marketplace", "hardware")):
        effort -= 8  # heavy to build

    # specificity (0-15)
    spec = 10
    if len(idea.get("pitch", "")) > 40:
        spec += 3
    if any(w in text for w in ("niche", "specific", "for", "who")):
        spec += 2
    if "generic" in text or len(idea.get("pitch", "")) < 20:
        spec -= 6

    total = max(0, min(100, monet + demand + effort + spec))
    return total


def rank(ideas):
    """Score + sort, keep top N."""
    for idea in ideas:
        idea["score"] = score_idea(idea)
    ranked = sorted(ideas, key=lambda x: x["score"], reverse=True)
    return ranked[:TOP_N]


# ── pipeline ─────────────────────────────────────────────────────────
def run_ideate():
    """Full stage 1-3: ideate → score → save top 20."""
    ideas = ideate()
    if not ideas:
        return {"ok": False, "error": "router failed to generate ideas"}
    # dedupe by slug (batches can overlap) + assign ids
    seen = set()
    deduped = []
    for idea in ideas:
        if idea["slug"] in seen:
            continue
        seen.add(idea["slug"])
        deduped.append(idea)
    for i, idea in enumerate(deduped):
        idea["id"] = i + 1
    top = rank(deduped)
    FACTORY_DIR.mkdir(exist_ok=True)
    IDEAS_FILE.write_text(json.dumps(deduped, ensure_ascii=False, indent=2), encoding="utf-8")
    TOP_FILE.write_text(json.dumps(top, ensure_ascii=False, indent=2), encoding="utf-8")
    log_action({"ts": datetime.now(timezone.utc).isoformat(),
                "stage": "ideate", "generated": len(deduped), "top": len(top)})
    return {"ok": True, "generated": len(deduped), "top": len(top),
            "best": top[0]["name"] if top else None}


def log_action(entry):
    log = []
    if LOG_FILE.exists():
        try:
            log = json.loads(LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            log = []
    log.append(entry)
    log = log[-100:]
    LOG_FILE.parent.mkdir(exist_ok=True)
    LOG_FILE.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")


def load_top():
    if not TOP_FILE.exists():
        return []
    try:
        return json.loads(TOP_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def find_app(slug):
    for app in load_top():
        if app.get("slug") == slug:
            return app
    return None


def status():
    ideas = []
    if IDEAS_FILE.exists():
        try:
            ideas = json.loads(IDEAS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    top = load_top()
    apps = list(APPS_DIR.glob("*/")) if APPS_DIR.exists() else []

    lines = ["🏭 *App Factory*", ""]
    lines.append(f"أفكار مولّدة: `{len(ideas)}`")
    lines.append(f"أحسن 20: `{len(top)}`")
    lines.append(f"apps مبنية (code): `{len(apps)}`")
    if top:
        lines += ["", "🏆 التوب 5:"]
        for a in top[:5]:
            lines.append(f"• `{a['score']}` [{a.get('category','?')}] {a['name']}")
    if apps:
        lines += ["", "📦 apps جاهزة:"]
        for d in apps[:5]:
            lines.append(f"• `{d.name}`")
    return "\n".join(lines)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="status", choices=["ideate", "mvp", "code", "status"])
    ap.add_argument("--slug", help="app slug for mvp/code")
    ap.add_argument("--idea", help="custom idea text for mvp/code")
    args = ap.parse_args()

    if args.cmd == "ideate":
        r = run_ideate()
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif args.cmd == "status":
        print(status())
    elif args.cmd in ("mvp", "code"):
        if not args.slug:
            print(json.dumps({"ok": False, "error": "--slug required"}, ensure_ascii=False))
            return
        from app_mvp import run_mvp, run_code
        r = run_mvp(args.slug) if args.cmd == "mvp" else run_code(args.slug)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(status())


if __name__ == "__main__":
    main()
