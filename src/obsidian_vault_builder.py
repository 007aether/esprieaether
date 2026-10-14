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
                "mini-qr", "GoBackup", "Secrux", "Vito"]


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

    # index
    idx = ["# 🧠 EsprieAether Vault", "",
           "## Services", ""] + [f"- [[{n}]] :{p}" for n, (p, _) in SERVICES.items()]
    idx += ["", "## Bots", ""] + [f"- [[{n}]]" for n in BOTS]
    idx += ["", "## Integrations", ""] + [f"- [[{n}]]" for n in INTEGRATIONS]
    idx += ["", "## Sunna", "", "- [[Sunna]]", "- [[devis]]", "- [[GMB]]", "- [[Netlify]]"]
    w(VAULT / "_Index.md", "\n".join(idx) + "\n")

    # services
    for name, (port, links) in SERVICES.items():
        w(VAULT / "Services" / f"{name}.md",
          note(name, ["service"], f"Port **{port}**.", links))

    # bots
    for name, links in BOTS.items():
        w(VAULT / "Bots" / f"{name}.md", note(name, ["bot"], "24/7 bot.", links))

    # integrations (one note each)
    for name in INTEGRATIONS:
        w(VAULT / "Integrations" / f"{name}.md",
          note(name, ["integration"], "Linked integration.", ["integrations", "control-center"]))

    # core concepts
    w(VAULT / "Sunna.md", note("Sunna", ["company"], "SARL AU — ICE 004054044000074 — Casablanca — 0770720602",
                                        ["sunna-api", "devis", "Netlify", "GMB", "kanban", "prices"]))
    w(VAULT / "devis.md", note("devis", ["sunna"], "Devis + facture builder (PDF). `bots/devis_builder.py` + `facture_builder.py`",
                                    ["Sunna", "price-tracker", "prices"]))
    w(VAULT / "Netlify.md", note("Netlify", ["web"], "Live site + keepalive. `Coordination/netlify_url.json`",
                                      ["netlify-keepalive", "Sunna"]))
    w(VAULT / "GMB.md", note("GMB", ["google"], "Google Business Profile. `Devis/gmb_profile.json`", ["Sunna"]))
    w(VAULT / "JEV.md", note("JEV", ["brain"], "System One typed decisions. `/decide` endpoint", ["router"]))
    w(VAULT / "Apollo-agent.md", note("Apollo-agent", ["agent"], "Deep research meta-agent. `aether-apollo`", ["router", "Apollo"]))
    w(VAULT / "OSINT.md", note("OSINT", ["jarvis"], "16 agents — face ID + swarm + synthesis", ["jarvis", "Exa"]))
    w(VAULT / "OKX.md", note("OKX", ["trading"], "Connector + trading bot (DRY-RUN). withdrawal refused by code", ["router"]))
    w(VAULT / "VPS.md", note("VPS", ["infra"], "SSH tunnel + zero-trust. `docs/VPS_TOR_DOCKER.md`", ["cloud-desktop", "Octelium"]))
    w(VAULT / "Tor.md", note("Tor", ["infra"], "3 documented fixes. `docs/VPS_TOR_DOCKER.md`", ["cloud-desktop", "VPS"]))
    w(VAULT / "DeepSeek-Harness.md", note("DeepSeek-Harness", ["agent"], "DSH — browser-capable agent", ["dsh-bridge"]))
    w(VAULT / "prices.md", note("prices", ["sunna"], "Live steel/galva/zinc. `Recherche/live_prices.json`", ["price-tracker", "PriceGhost"]))
    w(VAULT / "Exa.md", note("Exa", ["api"], "Neural search key", ["jarvis", "OSINT"]))
    w(VAULT / "Telegram.md", note("Telegram", ["bot"], "Commands: /sunna /sunnabilan /sunnadevis /sunnaprix /sunnanetlify /sunnakanban /jarvis /tm /integrations /okx", ["bot-heartbeat", "Sunna"]))
    w(VAULT / "control-center.md", note("control-center", ["web"], "http://localhost:5000/control", ["web", "homedock"]))
    w(VAULT / "all-services.md", note("all-services", ["meta"], "\n".join(f"[[{n}]]" for n in SERVICES), ["watchdog"]))
    w(VAULT / "all-integrations.md", note("all-integrations", ["meta"], "\n".join(f"[[{n}]]" for n in INTEGRATIONS), ["integrations"]))
    w(VAULT / "Anthropic.md", note("Anthropic", ["api"], "Claude key", ["jarvis"]))
    w(VAULT / "Gemini.md", note("Gemini", ["api"], "Gemini key", ["jarvis"]))

    # copy SOP + gap docs
    for src in ["SOP_WIKI.md", "GAP_ANALYSIS.md"]:
        s = ESPRIE / "docs" / src
        if s.exists():
            w(VAULT / s.name, s.read_text(encoding="utf-8"))

    n_notes = len(list(VAULT.rglob("*.md")))
    print(f"✅ Obsidian vault: {VAULT}")
    print(f"   {n_notes} notes — open it in Obsidian → graph view")
    print(f"   then: python integrations/obsidian-graphify (render graph.html)")


if __name__ == "__main__":
    main()
