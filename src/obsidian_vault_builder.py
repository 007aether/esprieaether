#!/usr/bin/env python3
"""
obsidian_vault_builder.py — build an Obsidian vault (knowledge graph)
from EsprieAether docs + Sunna files, with [[wiki-links]].

Creates: ~/ObsidianVault/EsprieAether/ with:
  - one note per service, bot, integration, SOP
  - wiki-links between them (services → bots → integrations)
  - _Index.md as the home
Then obsidian-graphify (integrations/) can render the graph.html.

Usage:
  python obsidian_vault_builder.py            # build/refresh the vault
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
VAULT = HOME / "ObsidianVault" / "EsprieAether"
ESPRIE = HOME / "Desktop" / "esprieaether"
SUNNA = HOME / "Desktop" / "Sunna-Equipe-Industrial"

# services: name -> (port, links)
SERVICES = {
    "ollama": (11434, ["router"]),
    "router": (11435, ["ollama", "orchestrator", "JEV", "Apollo-agent", "OKX"]),
    "orchestrator": (11436, ["router"]),
    "web": (5000, ["router", "cloud-desktop", "control-center"]),
    "cloud-desktop": (5001, ["web", "Tor", "VPS"]),
    "sunna-api": (5100, ["Sunna", "prices", "netlify", "kanban"]),
    "dsh-bridge": (5101, ["DeepSeek-Harness"]),
    "integrations": (5102, ["all-integrations"]),
    "kanban": (5103, ["Sunna", "Veritas-Kanban"]),
    "homedock": (5104, ["all-integrations", "control-center"]),
    "jarvis": (8000, ["OSINT", "Exa", "Anthropic", "Gemini"]),
}

BOTS = {
    "netlify-keepalive": ["Netlify", "Sunna"],
    "bot-heartbeat": ["Telegram", "watchdog"],
    "price-tracker": ["PriceGhost", "Sunna", "devis"],
    "sunna-web-bot": ["Netlify", "GMB", "Sunna"],
    "watchdog": ["all-services"],
}

INTEGRATIONS = ["Checkmate", "Portracker", "Ask4Me", "PriceGhost", "Cronpulse",
                "Octelium", "Veritas-Kanban", "FrankMD", "Homescreen-hero", "Kino",
                "Mimic", "xPrivo", "Outline", "HomeDock", "Apollo", "Superpowers",
                "REA", "Artcraft", "Hyperframes", "Hypit", "Dozzle", "Runtipi",
                "mini-qr", "GoBackup", "Secrux", "Vito", "obsidian-graphify",
                "freqtrade", "openstock", "promptfoo", "antislop", "openclaude",
                "openresearch", "claude-red", "hack-skills", "pwnproxy",
                "TraffMonetizer", "Pinterest", "Facebook", "YouTube"]

# agents: name -> links
AGENTS = {
    "airdrop": ["crypto"], "ask": ["router"], "bandwidth": ["infra"],
    "browser": ["infra"], "calendar": ["productivity"], "cloud": ["VPS"],
    "email": ["Sunna", "productivity"], "file": ["productivity"],
    "github": ["github"], "guardian": ["infra"], "hermes": ["router"],
    "jarvis-bridge": ["jarvis"], "market": ["crypto"], "needle": ["crypto"],
    "pharos": ["crypto"], "planner": ["productivity"],
    "terminal": ["infra"], "vault": ["security"], "vpn": ["VPN"],
    "research-monitor": ["research"], "semantic-memory": ["memory"],
}

# sunna topics: name -> (body, links)
SUNNA = {
    "Sunna": ("SARL AU — ICE 004054044000074 — Casablanca — 0770720602",
              ["sunna-api", "devis", "netlify", "GMB", "kanban", "prices"]),
    "devis": ("Devis + facture builder (PDF). `bots/devis_builder.py` + `facture_builder.py`",
              ["Sunna", "price-tracker", "prices"]),
    "prices": ("Live steel/galva/zinc. `Recherche/live_prices.json`",
               ["price-tracker", "PriceGhost", "Sunna"]),
    "netlify": ("Live site + keepalive. `Coordination/netlify_url.json`",
                ["netlify-keepalive", "Sunna"]),
    "GMB": ("Google Business Profile. `Devis/gmb_profile.json`", ["Sunna"]),
    "email": ("`bots/email_sender.py` — Gmail SMTP + .eml drafts. cc 007aether@gmail.com",
              ["Sunna", "devis"]),
    "qr": ("`bots/qr_generator.py` — QR for site + devis", ["Sunna", "netlify"]),
    "Pinterest": ("Social channel — `bots/pinterest_bot.py` (Hermes-driven pins). sunnaequipeindustrial@gmail.com", ["Sunna", "bandwidth", "social"]),
    "Facebook": ("Social channel — page + posts (browser/agent driven)", ["Sunna", "social"]),
    "YouTube": ("Social channel — video (browser/agent driven)", ["Sunna", "social"]),
    "social": ("Sunna social channels: Pinterest · Facebook · YouTube", ["Sunna", "Pinterest", "Facebook", "YouTube"]),
}

# brains: name -> (body, links)
BRAINS = {
    "JEV": ("System One typed decisions. `/decide` endpoint", ["router"]),
    "Apollo-agent": ("Deep research meta-agent. `aether-apollo`", ["router", "Apollo"]),
    "OSINT": ("16 agents — face ID + swarm + synthesis", ["jarvis", "Exa"]),
    "OKX": ("Connector + trading bot (DRY-RUN). withdrawal refused by code", ["router"]),
    "DeepSeek-Harness": ("DSH — browser-capable agent", ["dsh-bridge"]),
}

# infra: name -> (body, links)
INFRA = {
    "VPS": ("SSH tunnel + zero-trust. `docs/VPS_TOR_DOCKER.md`", ["cloud-desktop", "Octelium"]),
    "Tor": ("3 documented fixes. `docs/VPS_TOR_DOCKER.md`", ["cloud-desktop", "VPS"]),
    "VPN": ("WireGuard — `vpn_agent.py` + auto-reconnect daemon", ["infra", "cloud-desktop"]),
    "docker": ("homedock + dozzle + runtipi", ["homedock"]),
}

# meta: name -> (body, links)
META = {
    "control-center": ("http://localhost:5000/control", ["web", "homedock"]),
    "knowledge-graph": ("http://localhost:5000/obsidian — vis-network 64+ notes", ["obsidian-graphify", "web"]),
    "Telegram": ("Commands: /sunna /sunnabilan /sunnadevis /sunnaprix /sunnanetlify /sunnakanban /jarvis /tm /integrations /okx /obsidian", ["bot-heartbeat", "Sunna"]),
    "Anthropic": ("Claude key", ["jarvis"]),
    "Gemini": ("Gemini key", ["jarvis"]),
    "Exa": ("Neural search key", ["jarvis", "OSINT"]),
    "github": ("007aether — git CLI auth (no REST tokens)", ["github"]),
    "security": ("vault_agent — encrypted credential store", ["vault"]),
    "productivity": ("calendar + file + planner agents", ["calendar", "file", "planner"]),
    "memory": ("semantic-memory — persistent context", ["semantic-memory"]),
    "research": ("research-monitor — news 24/7", ["research-monitor"]),
    "crypto": ("airdrop + market + needle + pharos", ["airdrop", "market", "needle", "pharos"]),
    "bandwidth": ("bandwidth_agent + TraffMonetizer — passive income from traffic", ["TraffMonetizer", "infra"]),
}


def w(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def note(name, tags, body, links):
    fm = "---\ntags: [" + ", ".join(tags) + "]\nupdated: " + datetime.now(timezone.utc).strftime("%Y-%m-%d") + "\n---\n\n"
    linklines = "\n".join(f"- [[{l}]]" for l in links if l != name)
    return fm + f"# {name}\n\n{body}\n\n## Liens\n{linklines}\n"


def main():
    VAULT.mkdir(parents=True, exist_ok=True)
    (VAULT / ".obsidian").mkdir(exist_ok=True)

    # ── index ──
    idx = ["# 🧠 EsprieAether — Knowledge Graph", "",
           "## ⚙️ Services", ""] + [f"- [[{n}]] — :{p}" for n, (p, _) in SERVICES.items()]
    idx += ["", "## 🤖 Bots", ""] + [f"- [[{n}]]" for n in BOTS]
    idx += ["", "## 🧩 Agents", ""] + [f"- [[{n}]]" for n in AGENTS]
    idx += ["", "## 🔌 Integrations", ""] + [f"- [[{n}]]" for n in INTEGRATIONS]
    idx += ["", "## ☀️ Sunna", ""] + [f"- [[{n}]]" for n in SUNNA]
    idx += ["", "## 🧠 Brains", ""] + [f"- [[{n}]]" for n in BRAINS]
    idx += ["", "## 🔴 Infra", ""] + [f"- [[{n}]]" for n in INFRA]
    idx += ["", "## 📚 Docs", "", "- [[SOP_WIKI]]", "- [[GAP_ANALYSIS]]"]
    idx += ["", "## 🔗 Meta", ""] + [f"- [[{n}]]" for n in META]
    w(VAULT / "_Index.md", "\n".join(idx) + "\n")

    # ── services ──
    for name, (port, links) in SERVICES.items():
        w(VAULT / "Services" / f"{name}.md",
          note(name, ["service", "core"], f"Port **{port}** — http://localhost:{port}/", links))

    # ── bots ──
    for name, links in BOTS.items():
        w(VAULT / "Bots" / f"{name}.md", note(name, ["bot", "core"], "24/7 bot.", links))

    # ── agents ──
    for name, links in AGENTS.items():
        w(VAULT / "Agents" / f"{name}.md",
          note(name, ["agent", "core"], f"Agent `src/{name.replace('-', '_')}_agent.py`", links))

    # ── integrations ──
    for name in INTEGRATIONS:
        w(VAULT / "Integrations" / f"{name}.md",
          note(name, ["integration"], "Linked integration — `integrations/`", ["integrations", "control-center"]))

    # ── sunna ──
    for name, (body, links) in SUNNA.items():
        w(VAULT / "Sunna" / f"{name}.md", note(name, ["sunna", "company"], body, links))

    # ── brains ──
    for name, (body, links) in BRAINS.items():
        w(VAULT / "Brains" / f"{name}.md", note(name, ["brain", "core"], body, links))

    # ── infra ──
    for name, (body, links) in INFRA.items():
        w(VAULT / "Infra" / f"{name}.md", note(name, ["infra", "core"], body, links))

    # ── meta ──
    for name, (body, links) in META.items():
        w(VAULT / "Meta" / f"{name}.md", note(name, ["meta"], body, links))

    # ── docs (SOP + GAP — filed under Docs/, tagged) ──
    for src_name, tags in [("SOP_WIKI.md", ["doc", "sop"]), ("GAP_ANALYSIS.md", ["doc", "gap"])]:
        s = ESPRIE / "docs" / src_name
        stem = src_name.replace(".md", "")
        if s.exists():
            body = s.read_text(encoding="utf-8", errors="ignore")
            fm = "---\ntags: [" + ", ".join(tags) + "]\nupdated: " + datetime.now(timezone.utc).strftime("%Y-%m-%d") + "\n---\n\n"
            if not body.startswith("---"):
                body = fm + body
            w(VAULT / "Docs" / f"{stem}.md", body)
        else:
            w(VAULT / "Docs" / f"{stem}.md", note(stem, tags, "_not found_", ["_Index"]))

    # ── remove stale root-level doc copies (now under Docs/) ──
    for stale in ["SOP_WIKI.md", "GAP_ANALYSIS.md"]:
        p = VAULT / stale
        if p.exists():
            p.unlink()

    n_notes = len(list(VAULT.rglob("*.md")))
    print(f"✅ Obsidian vault: {VAULT}")
    print(f"   {n_notes} notes")
    for d in ["Services", "Bots", "Agents", "Integrations", "Sunna", "Brains", "Infra", "Docs", "Meta"]:
        cnt = len(list((VAULT / d).glob("*.md")))
        print(f"   {d}: {cnt}")
    print(f"   graph: python src/obsidian_graph_web.py")


if __name__ == "__main__":
    main()
