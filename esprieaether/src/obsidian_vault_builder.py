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
# Le projet réel est le parent de src/ ; l'ancien chemin ~/Desktop/esprieaether
# n'existe pas sur cette machine et produisait des notes "_not found_".
ROOT = Path(__file__).resolve().parents[1]
ESPRIE = Path(os.getenv("ESPRIE_DIR", str(ROOT)))
SUNNAVOK_ROOT = Path(os.getenv("SUNNAVOK_DIR", str(ROOT.parent)))
VAULT = Path(os.getenv("OBSIDIAN_VAULT_DIR", str(HOME / "ObsidianVault" / "EsprieAether")))

# Catalogue réel des cerveaux GGUF (même source que le routeur :31416).
try:
    from local_brain import CATALOG as LOCAL_BRAIN_CATALOG, available_models as _local_models
except Exception:  # pragma: no cover - le routeur reste optionnel pour les tests
    LOCAL_BRAIN_CATALOG = []
    def _local_models():
        return []


def local_brain_status() -> str:
    """État honnête du routeur local : complet seulement si les GGUF sont vérifiés."""
    ready = [m["id"] for m in _local_models()]
    if ready:
        return ("✅ Vérifié : routeur :31416 actif, modèles complets : "
                + ", ".join(ready) + ". JARVIS/Hermes les utilisent en priorité.")
    return ("⏳ Routeur :31416 actif (`/health` 200) mais **0 modèle complet** : "
            "les GGUF se téléchargent avec vérification taille + SHA256. "
            "JARVIS/Hermes utilisent le repli :31415 jusqu'à la fin du téléchargement.")


def local_brain_entries() -> dict:
    """Une note par GGUF réel du catalogue, jamais un modèle imaginé."""
    entries = {}
    for model in LOCAL_BRAIN_CATALOG:
        ready = any(m["id"] == model["id"] for m in _local_models())
        state = ("✅ Complet et disponible sur :31416" if ready
                 else "⏳ Téléchargement en cours — non annoncé tant que la taille HF n'est pas atteinte")
        entries[model["id"]] = (
            f"{model['label']} — GGUF Q4_K_M local (CPU, loopback). {state}. "
            f"Fichier : `{model['file']}`.",
            ["local-brain", "jarvis", "router", "director"],
        )
    return entries

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
    "jarvis": (5000, ["local-brain", "router", "freellmapi", "OSINT", "Exa", "Anthropic", "Gemini"]),
    "jarvis-frontend": (3000, ["jarvis", "OSINT"]),
    "freellmapi": (31415, ["web", "cloud-desktop", "local-brain"]),
    "local-brain": (31416, ["jarvis", "router", "freellmapi", "director"]),
}

# État vérifié le 22/11/2026. Les services non confirmés restent dans le graphe
# mais sont marqués comme déclarations historiques, pas comme services réels.
SERVICE_STATUS = {
    "web": "✅ Vérifié : Flask/JARVIS, `/api/health` 200.",
    "jarvis": ("✅ Vérifié : JARVIS est le service Flask sur **:5000** (`/api/health` 200). "
               "Ses routes `/api/hermes` et `/api/hermes/status` passent par `HermesBridge`, "
               "qui interroge d'abord le routeur local **:31416**, puis :31415 en repli."),
    "cloud-desktop": "✅ Vérifié : passerelle EspriaAether :5001 (auth JWT, KPI SQLite, LLM).",
    "sunna-api": "✅ Vérifié : API dashboard Node, 3/3 tests verts, persistance confirmée.",
    "freellmapi": "✅ Vérifié : API OpenAI-compatible, chat `PONG` via `gemini-flash-lite`. Repli du chat local.",
    "ollama": "⏸ Arrêté volontairement : modèle non téléchargé (CDN fournisseur en échec) ; dernier fallback uniquement.",
}
UNVERIFIED = "⚠️ Non vérifié dans cet environnement — déclaration historique, pas un service confirmé."

BOTS = {
    "netlify-keepalive": ["Netlify", "Sunna"],
    "bot-heartbeat": ["Telegram", "watchdog"],
    "price-tracker": ["PriceGhost", "Sunna", "devis"],
    "sunna-web-bot": ["Netlify", "GMB", "Sunna"],
    "watchdog": ["all-services"],
    "espria-report": ["cloud-desktop", "sunna-api", "director"],
}

BOT_STATUS = {
    "espria-report": "✅ Vérifié : `espria_bot.py` génère un rapport réel depuis :5001 et l'écrit dans `data/logs/bot_test.log`. Mode **dry-run** par défaut : aucun appel Telegram sans `TELEGRAM_LIVE=1` explicite. Les tokens bot1/bot2 sont refusés par Telegram (401).",
    "bot-heartbeat": "⚠️ Historique : les tokens Telegram des deux bots sont refusés (401) ; aucun envoi réel possible actuellement.",
}

INTEGRATIONS = ["Checkmate", "Portracker", "Ask4Me", "PriceGhost", "Cronpulse",
                "Octelium", "Veritas-Kanban", "FrankMD", "Homescreen-hero", "Kino",
                "Mimic", "xPrivo", "Outline", "HomeDock", "Apollo", "Superpowers",
                "REA", "Artcraft", "Hyperframes", "Hypit", "Dozzle", "Runtipi",
                "mini-qr", "GoBackup", "Secrux", "Vito", "obsidian-graphify",
                "freqtrade", "openstock", "promptfoo", "antislop", "openclaude",
                "openresearch", "claude-red", "hack-skills", "pwnproxy",
                "TraffMonetizer", "Pinterest", "Facebook", "YouTube",
                "governor-edr",
                "agent-skills", "21st-magic-mcp", "fish-audio", "free-llm-apis",
                "strix", "claude-mem"]

# agents: name -> links
AGENTS = {
    "airdrop": ["crypto"], "ask": ["router"], "bandwidth": ["infra"],
    "browser": ["infra"], "calendar": ["productivity"], "cloud": ["VPS"],
    "email": ["Sunna", "productivity"], "file": ["productivity"],
    "github": ["cloud", "VPS", "Sunna"], "guardian": ["infra"], "hermes": ["router"],
    "jarvis-bridge": ["jarvis"], "market": ["crypto"], "needle": ["crypto"],
    "pharos": ["crypto"], "planner": ["productivity"],
    "terminal": ["infra"], "vault": ["security"], "vpn": ["VPN"],
    "research-monitor": ["research"], "semantic-memory": ["memory"],
    "rea": ["REA", "Ghidra", "reverse-engineering"],
    "deepseek-harness": ["deepseek", "brain", "ai", "skil"],
    "colibri": ["colibri", "router"],
    "orchestrator": ["mesh", "infra"],
    "digest": ["mesh", "infra"],
    "skill-harvester": ["mesh", "research"],
    "work-organizer": ["productivity"],
    "self-heal": ["guardian", "infra"],
    # Rôles déclarés dans le vault obsidian legacy, exposés par espria_system.
    "A1": ["sunna-api", "f-a"],
    "A2": ["sunna-api", "prices", "g-rate"],
    "A3": ["sunna-api", "_Index"],
    "A4": [],
    "M1": ["sunna-api", "products"],
    "L1": [],
    "L2": [],
    "director": ["cloud-desktop", "A1", "A2", "A3"],
}

REAL_AGENTS = {"A1", "A2", "A3", "A4", "M1", "L1", "L2", "director"}
NO_DATA_AGENTS = {"A4", "L1", "L2"}
AGENT_STATUS = {
    "A1": "Source réelle : `f-a` depuis la dashboard :5100.",
    "A2": "Source réelle : `g-rate`, `g-cons`, `g-margin` depuis la dashboard :5100.",
    "A3": "Source réelle : liste des tâches (`todo`) depuis la dashboard :5100.",
    "M1": "Source réelle : produits et inventaire depuis la dashboard :5100.",
    "director": "Synthèse des 8 agents + KPI SQLite + état du LLM.",
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
    "colibri": ("Qwen3-Coder-30B-A3B MoE (19.4GB, D:) — `coli serve` :8000 — strongest local brain, wired to router", ["router", "ai_router", "colibri_launcher"]),
    "ollama-local": ("⏸ qwen2.5:3b — arrêté, conservé comme **dernier** fallback. "
                     "Remplacé dans l'usage courant par les 3 GGUF uncensored du routeur :31416.", ["router", "local-brain"]),
    "mesh": ("7-agent mesh — evolve/security/research/market/quality/redteam/general — shared board :11437", ["router", "agent_mesh", "evolve", "security", "research"]),
    "REA": ("Reverse Engineer Anything (morluto/rea 226K) — Ghidra 12.1.4 + JDK 25 — native PE + JS/Electron analysis", ["rea_agent", "Ghidra"]),
    "JARVIS-intel": ("Real-time person intelligence — Next.js :3000 + FastAPI :8000 — capture/identify/research", ["jarvis", "IntelBoard"]),
    "Ghidra": ("12.1.4 + JDK 25 — REA analysis engine (D:/AetherData/rea)", ["REA", "rea_agent"]),
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
    "github": ("007aether — git CLI auth (no REST tokens)", ["cloud", "VPS", "Sunna"]),
    "security": ("vault_agent — encrypted credential store", ["vault"]),
    "productivity": ("calendar + file + planner agents", ["calendar", "file", "planner"]),
    "memory": ("semantic-memory — persistent context", ["semantic-memory"]),
    "research": ("research-monitor — news 24/7", ["research-monitor"]),
    "crypto": ("airdrop + market + needle + pharos", ["airdrop", "market", "needle", "pharos"]),
    "bandwidth": ("bandwidth_agent + TraffMonetizer — passive income from traffic", ["TraffMonetizer", "infra"]),
    "governor-edr": ("Local-first Windows threat detection agent (4B LLM + MITRE + YARA + Telegram HITL). integrations/governor-edr", ["security", "guardian", "infra", "Telegram"]),
}


def w(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def note(name, tags, body, links):
    fm = "---\ntags: [" + ", ".join(tags) + "]\nupdated: " + datetime.now(timezone.utc).strftime("%Y-%m-%d") + "\n---\n\n"
    linklines = "\n".join(f"- [[{l}]]" for l in links if l != name)
    return fm + f"# {name}\n\n{body}\n\n## Liens\n{linklines}\n"


def _import_note(src: Path, target: Path, category: str, links: list[str]) -> None:
    """Copie une note historique telle quelle, avec frontmatter et liens ajoutés."""
    text = src.read_text(encoding="utf-8", errors="ignore")
    if not text.startswith("---"):
        text = (f"---\ntags: [{category}, imported]\n"
                f"source: {src.relative_to(SUNNAVOK_ROOT).as_posix()}\n---\n\n") + text
    if "## Liens" not in text:
        text = text.rstrip() + "\n\n## Liens\n" + "\n".join(f"- [[{l}]]" for l in links) + "\n"
    w(target, text)


def import_archives() -> int:
    """Importe TOUTES les notes anciennes : vault legacy + notes du vault racine."""
    if not SUNNAVOK_ROOT.exists():
        return 0
    count = 0
    legacy = SUNNAVOK_ROOT / "07_Obsidian_Legacy" / "Sunna-Equipe-Industrial"
    if legacy.exists():
        for src in sorted(legacy.glob("*.md")):
            _import_note(src, VAULT / "Legacy" / src.name, "legacy",
                         ["_Index", "Sunna", "knowledge-graph"])
            count += 1
    for src in sorted(SUNNAVOK_ROOT.glob("*.md")):
        if src.name.startswith("_"):
            continue
        _import_note(src, VAULT / "SUNNAVOK" / f"ROOT__{src.stem}.md", "sunnavok",
                     ["_Index", "Sunna"])
        count += 1
    for folder in ("01_Company", "02_Branches", "03_Projects",
                   "04_Commercial", "05_Operations", "06_Templates"):
        directory = SUNNAVOK_ROOT / folder
        if not directory.exists():
            continue
        for src in sorted(directory.rglob("*.md")):
            rel = src.relative_to(directory).with_suffix("")
            stem = "__".join(rel.parts)
            _import_note(src, VAULT / "SUNNAVOK" / f"{folder}__{stem}.md", "sunnavok",
                         ["_Index", "Sunna"])
            count += 1
    return count


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
    idx += ["", "## 🧠 Brains", ""] + [f"- [[{n}]]" for n in {**BRAINS, **local_brain_entries()}]
    idx += ["", "## 🔴 Infra", ""] + [f"- [[{n}]]" for n in INFRA]
    idx += ["", "## 📚 Docs", "", "- [[SOP_WIKI]]", "- [[GAP_ANALYSIS]]"]
    idx += ["", "## 🔗 Meta", ""] + [f"- [[{n}]]" for n in META]
    w(VAULT / "_Index.md", "\n".join(idx) + "\n")

    # ── services ──
    for name, (port, links) in SERVICES.items():
        status = (local_brain_status() if name == "local-brain"
                  else SERVICE_STATUS.get(name, UNVERIFIED))
        w(VAULT / "Services" / f"{name}.md",
          note(name, ["service", "core"], f"Port **{port}** — http://localhost:{port}/\n\n{status}", links))

    # ── bots ──
    for name, links in BOTS.items():
        body = BOT_STATUS.get(name, "⚠️ Non vérifié dans cet environnement — bot déclaré historiquement.")
        w(VAULT / "Bots" / f"{name}.md", note(name, ["bot", "core"], body, links))

    # ── agents ──
    for name, links in AGENTS.items():
        if name == "self-heal":
            # note: bots/self_heal.py not yet present -> planned, not implemented
            body = "Planned — self-heal agent (`bots/self_heal.py`). Not yet implemented."
            tags = ["agent", "core", "planned"]
        elif name in REAL_AGENTS:
            endpoint = f"`GET /agents/{name}/run` sur la passerelle :5001."
            if name in NO_DATA_AGENTS:
                body = f"{endpoint} État : `no_data_source` — aucune source vérifiée, aucune affirmation inventée."
                tags = ["agent", "core", "no_data_source"]
            else:
                body = f"{endpoint} {AGENT_STATUS.get(name, '')}"
                tags = ["agent", "core", "verified"]
        else:
            body = f"Agent `src/{name.replace('-', '_')}_agent.py` — ⚠️ non vérifié dans cet environnement."
            tags = ["agent", "core", "unverified"]
        w(VAULT / "Agents" / f"{name}.md",
          note(name, tags, body, links))

    # ── integrations ──
    for name in INTEGRATIONS:
        w(VAULT / "Integrations" / f"{name}.md",
          note(name, ["integration"], "Linked integration — `integrations/`", ["integrations", "control-center"]))

    # ── sunna ──
    for name, (body, links) in SUNNA.items():
        w(VAULT / "Sunna" / f"{name}.md", note(name, ["sunna", "company"], body, links))

    # ── brains ── (les 3 GGUF locaux viennent du catalogue réel du routeur)
    all_brains = dict(BRAINS)
    all_brains.update(local_brain_entries())
    for name, (body, links) in all_brains.items():
        w(VAULT / "Brains" / f"{name}.md", note(name, ["brain", "core"], body, links))

    # ── infra ──
    for name, (body, links) in INFRA.items():
        w(VAULT / "Infra" / f"{name}.md", note(name, ["infra", "core"], body, links))

    # ── meta ──
    for name, (body, links) in META.items():
        w(VAULT / "Meta" / f"{name}.md", note(name, ["meta"], body, links))

    # ── synthèse auditable : sépare le vérifié du simplement déclaré ──
    status = ["# État vérifié — 22/11/2026", "", "## ✅ Confirmé (HTTP / tests)", ""]
    status += [f"- {name} : :{port} — {SERVICE_STATUS[name]}"
               for name, (port, _) in SERVICES.items() if name in SERVICE_STATUS]
    status += [f"- local-brain : :31416 — {local_brain_status()}"]
    status += ["", "## 🧠 Cerveaux locaux (Hugging Face, non censurés)", ""]
    status += [f"- {model['id']} : `{model['file']}` — "
               + ("✅ complet" if any(m["id"] == model["id"] for m in _local_models())
                  else "⏳ téléchargement en cours, non annoncé par le routeur")
               for model in LOCAL_BRAIN_CATALOG]
    status += ["- Priorité dans `HermesBridge` et `/chat/completions` : local :31416 → :31415 → Ollama (dernier recours)."]
    status += ["", "## ⚠️ Déclarations historiques non vérifiées", ""]
    status += [f"- {name} : :{port}" for name, (port, _) in SERVICES.items()
               if name not in SERVICE_STATUS]
    status += ["", "## 🤖 Bots", "",
               "- `espria-report` : dry-run vérifié (3/3 tests). Aucun appel Telegram sans `TELEGRAM_LIVE=1` explicite.",
               "- `bot1` / `bot2` : tokens refusés par Telegram (401) — envoi réel impossible.",
               "", "## 🧠 Agents", ""]
    status += [f"- {a} : " + ("`no_data_source` — aucune source vérifiée"
                              if a in NO_DATA_AGENTS else "source réelle : dashboard :5100 + KPI SQLite")
               for a in sorted(REAL_AGENTS)]
    archives = import_archives()
    status += ["", "## 🗄️ Archives importées (contenu conservé, non vérifié)", "",
               f"- {archives} notes anciennes copiées dans `Legacy/` et `SUNNAVOK/` sans suppression.",
               "- Leur présence dans le graphe ne signifie pas que les services décrits sont actifs.",
               "", "## ❓ Sources encore manquantes", "",
               "- `A4` (Legal) : aucun texte légal vérifié → `no_data_source`.",
               "- `L1` (Fiscalité) : aucun barème vérifié → `no_data_source`.",
               "- `L2` (Travail) : aucun texte social vérifié → `no_data_source`.",
               "- Déposer les documents dans `esprieaether/data/sources/{legal,fiscal,travail}/` : les agents les lisent alors tels quels."]
    w(VAULT / "Meta" / "ETAT_VERIFIE.md", "\n".join(status) + "\n")

    # ── docs (SOP + GAP — filed under Docs/, tagged) ──
    # WHY links injected here: graph_fixer adds links to the VAULT copy, but this
    # builder rewrites these notes from docs/ on every run, wiping them. Inject
    # a Related section here so links survive rebuilds.
    DOC_LINKS = {
        "SOP_WIKI": ["devis", "Sunna", "prices", "factures", "kanban", "all-services"],
        "GAP_ANALYSIS": ["all-services", "control-center", "SOP_WIKI", "all-integrations"],
    }
    for src_name, tags in [("SOP_WIKI.md", ["doc", "sop"]), ("GAP_ANALYSIS.md", ["doc", "gap"])]:
        s = ESPRIE / "docs" / src_name
        stem = src_name.replace(".md", "")
        if s.exists():
            body = s.read_text(encoding="utf-8", errors="ignore")
            fm = "---\ntags: [" + ", ".join(tags) + "]\nupdated: " + datetime.now(timezone.utc).strftime("%Y-%m-%d") + "\n---\n\n"
            if not body.startswith("---"):
                body = fm + body
            # inject wiki-links so the note is part of the graph (survives rebuild)
            rel = DOC_LINKS.get(stem, [])
            if rel and "## 🔗 Related" not in body:
                link_lines = "\n".join(f"- [[{l}]]" for l in rel)
                body = body.rstrip() + f"\n\n---\n\n## 🔗 Related\n\n{link_lines}\n"
            w(VAULT / "Docs" / f"{stem}.md", body)
        else:
            w(VAULT / "Docs" / f"{stem}.md", note(stem, tags, "_not found_", ["_Index"]))

    # ── remove stale root-level doc copies (now under Docs/) ──
    for stale in ["SOP_WIKI.md", "GAP_ANALYSIS.md"]:
        p = VAULT / stale
        if p.exists():
            p.unlink()

    n_notes = len(list(VAULT.rglob("*.md")))
    print(f"OK Obsidian vault: {VAULT}")
    print(f"   {n_notes} notes")
    for d in ["Services", "Bots", "Agents", "Integrations", "Sunna", "Brains", "Infra", "Docs", "Meta"]:
        cnt = len(list((VAULT / d).glob("*.md")))
        print(f"   {d}: {cnt}")
    print(f"   graph: python src/obsidian_graph_web.py")


if __name__ == "__main__":
    main()
