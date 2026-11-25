"""
integrations.py — Aether Intelligence Integrations
دمج 11 مشروع GitHub ف EsprieAether + DSH + Router

الهدف: نظام واحد يتطور ذاتياً عبر 11 طبقة ذكاء:
1. hack-skills (yaklang) — offensive security agent skills
2. claude-red (SnailSploit) — red team skill library
3. antislop (sam-paech) — output quality filtering
4. openclaude (Twigpine) — runs anywhere framework
5. openresearch (alphaXiv) — research agent mode
6. openstock (Open-Dev-Society) — market analysis
7. pwnproxy (ericmtzmtz) — local-first pentest platform
8. minimax — free AI provider (router brain #4)
9. wa-kg — whatsapp knowledge graph (Sunna client tracking)
10. potatomesh — mesh networking (decentralized AI)
11. promptfoo — agent testing/red-teaming
"""

import json
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
INTEGRATIONS_DIR = ROOT / "integrations"
INTEGRATIONS_DIR.mkdir(exist_ok=True)

# ── Integration registry ──
# كل integration: اسم → {repo, brain?, skill?, use}
INTEGRATIONS = {
    "hack-skills": {
        "repo": "https://github.com/yaklang/hack-skills.git",
        "type": "skill_pack",
        "use": "offensive security agent skills → HexStrike robot",
    },
    "claude-red": {
        "repo": "https://github.com/SnailSploit/Claude-Red.git",
        "type": "skill_pack",
        "use": "red team skill library → HexStrike robot",
    },
    "antislop": {
        "repo": "https://github.com/sam-paech/antislop-sampler.git",
        "type": "filter",
        "use": "output quality filter → router middleware",
    },
    "openclaude": {
        "repo": "https://github.com/Twigpine/openclaude.git",
        "type": "framework",
        "use": "portable agent runtime → DSH alternative",
    },
    "openresearch": {
        "repo": "https://github.com/alphaXiv/OpenResearch.git",
        "type": "agent_mode",
        "use": "research mode → /research command",
    },
    "openstock": {
        "repo": "https://github.com/Open-Dev-Society/OpenStock.git",
        "type": "tool",
        "use": "market analysis → STOCK_ANALYZER robot",
    },
    "pwnproxy": {
        "repo": "https://github.com/ericmtzmtz/pwnproxy.git",
        "type": "platform",
        "use": "local-first pentest → security robot",
    },
    "promptfoo": {
        "repo": "https://github.com/promptfoo/promptfoo.git",
        "type": "testing",
        "use": "agent red-teaming → self_evolve validation",
    },
}


def clone_integrations():
    """Clone all integration repos (shallow, fast)."""
    import subprocess
    results = {}
    for name, info in INTEGRATIONS.items():
        dest = INTEGRATIONS_DIR / name
        if dest.exists():
            results[name] = "already cloned"
            continue
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", info["repo"], str(dest)],
                capture_output=True, timeout=120, check=True,
            )
            results[name] = "cloned"
        except Exception as e:
            results[name] = f"error: {str(e)[:60]}"
    return results


def scan_integrations():
    """Scan what's available in each integration."""
    report = {}
    for name in INTEGRATIONS:
        dest = INTEGRATIONS_DIR / name
        if not dest.exists():
            report[name] = {"status": "not cloned"}
            continue
        files = list(dest.glob("*.py")) + list(dest.glob("*.md")) + list(dest.glob("*.sh"))
        report[name] = {
            "status": "ready",
            "files": len(files),
            "type": INTEGRATIONS[name]["type"],
            "use": INTEGRATIONS[name]["use"],
        }
    return report


def add_minimax_brain():
    """Add MiniMax as router brain #4 (free, no key needed for basic)."""
    env_path = ROOT / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    # check if already added
    if any("MINIMAX" in l for l in lines):
        return "already configured"
    lines += [
        "",
        "# MiniMax free tier (integration brain)",
        "MINIMAX_BASE_URL=https://api.minimax.chat/v1",
        "MINIMAX_MODEL=abab6.5s-chat",
    ]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "added"


if __name__ == "__main__":
    import sys
    action = sys.argv[1] if len(sys.argv) > 1 else "scan"

    if action == "clone":
        r = clone_integrations()
        print(json.dumps(r, indent=2))
    elif action == "scan":
        r = scan_integrations()
        print(json.dumps(r, indent=2, ensure_ascii=False))
    elif action == "minimax":
        print(add_minimax_brain())
