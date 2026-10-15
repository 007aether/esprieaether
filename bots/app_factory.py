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
    try:
        data = json.dumps({
            "model": "aether-auto", "messages": messages,
            "max_tokens": max_tokens, "temperature": 0.8,
        }).encode()
        req = urllib.request.Request(f"{ROUTER_URL}/v1/chat/completions", data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            result = json.loads(r.read().decode())
            return result["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"router error: {e}")
        return None


# ── STAGE 1: ideate ──────────────────────────────────────────────────
IDEATE_PROMPT = """Generate {n} distinct mobile app ideas that are:
- in HIGH demand (people actively pay for this category)
- monetizable via subscription (RevenueCat-friendly: a clear pro feature)
- buildable as an MVP by a solo dev in 1-2 weeks (React Native / Expo)
- NOT a clone of an existing saturated app, but a sharp niche wedge

Focus areas (pick across these, weight toward underserved niches):
productivity, health/fitness, finance/budgeting, education/language,
AI-utilities, creator tools, niche B2B tools, local/services,
habit trackers, note-taking, meal/food, travel, sleep, focus, relationships.

Respond with ONLY a JSON array (no prose, no fences):
[
  {{"name": "App Name", "slug": "app-name", "category": "productivity",
    "pitch": "one sentence on what it does and for whom",
    "monetization": "how it makes money (what the pro feature is)",
    "audience": "who pays"}}
]
Make every idea concrete and specific (no generic 'todo app'). {n} entries."""


def ideate(n=N_IDEAS):
    """Generate n app ideas via the router."""
    logger.info(f"💡 generating {n} app ideas...")
    raw = ask_router(IDEATE_PROMPT.format(n=n), max_tokens=4000, timeout=180)
    if not raw:
        return []
    # strip fences if present
    raw = raw.strip()
    raw = re.sub(r"^```(json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()
    # extract JSON array
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if not m:
        logger.error("no JSON array in response")
        return []
    try:
        ideas = json.loads(m.group(0))
    except Exception as e:
        logger.error(f"JSON parse failed: {e}")
        return []
    # normalize + slugify
    for i, idea in enumerate(ideas):
        idea["id"] = i + 1
        slug = idea.get("slug") or idea.get("name", f"app-{i}")
        idea["slug"] = re.sub(r"[^a-z0-9]+", "-", slug.lower()).strip("-")
    logger.info(f"✅ generated {len(ideas)} ideas")
    return ideas


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
    top = rank(ideas)
    FACTORY_DIR.mkdir(exist_ok=True)
    IDEAS_FILE.write_text(json.dumps(ideas, ensure_ascii=False, indent=2), encoding="utf-8")
    TOP_FILE.write_text(json.dumps(top, ensure_ascii=False, indent=2), encoding="utf-8")
    log_action({"ts": datetime.now(timezone.utc).isoformat(),
                "stage": "ideate", "generated": len(ideas), "top": len(top)})
    return {"ok": True, "generated": len(ideas), "top": len(top),
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
