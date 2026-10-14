#!/usr/bin/env python3
"""
integrations_adapter.py — unified status + control for the 16 GitHub
integrations cloned into esprieaether/integrations/.

Exposes on port 5102:
  GET  /health        — adapter alive
  GET  /list          — all integrations + detected stack + status
  GET  /status/<name> — one integration's ports/health
  POST /scan          — rescan integrations dir (Portracker-style)

Design: this is the "port map" layer. Checkmate/Portracker/Cronpulse
logic is folded in here (no need to run their full stacks) so the
control center + Telegram get one live view of everything.
"""

import json
import os
import socket
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = Flask(__name__)
PORT = int(os.getenv("INTEGRATIONS_PORT", "5102"))
INT_DIR = Path(__file__).resolve().parent.parent / "integrations"

# name -> (repo, role, priority, how we use it)
CATALOG = {
    "checkmate":        ("bluewave-labs/Checkmate",        "uptime monitoring",        "high",   "watchdog + site uptime"),
    "portracker":       ("mostafa-wahied/Portracker",      "port/service discovery",   "easy",   "live port map"),
    "ask4me":           ("easychen/ask4me",                "human-in-the-loop",        "med",    "approve risky actions"),
    "PriceGhost":       ("clucraft/PriceGhost",            "AI price tracker",         "high",   "track steel/galva prices"),
    "invoice-builder":  ("piratuks/invoice-builder",       "offline invoicing",        "high",   "PDF invoices (devis+facture, folded)"),
    "cronpulse":        ("techfort/cronpulse-community",   "cron monitor + alerts",    "high",   "alert if bots die (heartbeat)"),
    "octelium":         ("octelium/octelium",              "zero-trust access",        "med",    "secure services"),
    "veritas-kanban":   ("BradGroux/veritas-kanban",       "markdown kanban + agents", "med",    "task board (:5103, folded)"),
    "FrankMD":          ("akitaonrails/FrankMD",           "markdown blog editor",     "easy",   "Sunna blog (SEO)"),
    "homescreen-hero":  ("trentferguson/homescreen-hero",  "media dashboard",          "easy",   "media widgets"),
    "kino":             ("mmcdole/kino",                   "terminal Plex client",     "easy",   "media control"),
    "mimic":            ("littledivy/mimic",               "app→python client",        "med",    "auto API clients"),
    "xprivo":           ("xprivo/ai-chat",                 "privacy AI chat",          "med",    "customer AI assistant"),
    "outline":          ("easychen/outline",               "knowledge base",           "med",    "team wiki/SOPs"),
    "homedock":         ("BansheeTech/HomeDockOS",         "homelab OS dashboard",     "easy",   "widget dashboard (:5104, folded)"),
    "apollo":           ("manasseh-zw/apollo",             "deep research meta-agent", "high",   "research coordinator (aether-apollo)"),
    "superpowers":      ("obra/superpowers",               "dev methodology skills",   "med",    "agent skills library"),
    "rea":              ("morluto/rea",                    "reverse engineer anything","med",    "app → API client"),
    "artcraft":         ("storytold/artcraft",             "AI creative/media",        "med",    "product images/video"),
    "hyperframes":      ("heygen-com/hyperframes",         "AI video frames",          "med",    "marketing video"),
    "hypit":            ("hypit-ai/hypit",                 "AI agent toolkit",         "med",    "agent skills (folded)"),
    "dozzle":           ("amir20/dozzle",                  "docker log viewer",        "easy",   "docker logs UI (folded)"),
    "runtipi":          ("runtipi/runtipi",                "homeserver app store",    "easy",   "app manager (folded)"),
    "mini-qr":          ("lyqht/mini-qr",                  "minimal QR generator",     "easy",   "QR codes (qr_generator.py, folded)"),
    "gobackup":         ("gobackup/gobackup",              "backup tool",              "med",    "auto backup (folded)"),
    "secrux":           ("Master-lay/secrux",              "security scanner",         "med",    "security scans (folded)"),
    "vito":             ("vitodeploy/vito",                "server deployment",        "med",    "VPS deploy (folded)"),
    "obsidian-graphify":("Chandlersn/obsidian-graphify",   "notes → knowledge graph",  "med",    "vault graph (obsidian_vault_builder.py)"),
}

# integrations that are FOLDED into our stack (native adapter, no external clone)
FOLDED = {
    "invoice-builder": 5103,   # no — invoices via devis/facture builder
}
# actual folded services (native, running in-stack):
FOLDED_SERVICES = {
    "invoice-builder": None,       # bots/devis_builder.py + facture_builder.py (PDF)
    "veritas-kanban": "http://127.0.0.1:5103/health",
    "homedock": "http://127.0.0.1:5104/health",
    "hypit": None,                 # agent toolkit — folded into ECC skills
    "dozzle": None,                # docker logs — use `docker logs` / desktop UI
    "runtipi": None,               # app manager — use our control center
    "mini-qr": None,               # bots/qr_generator.py
    "gobackup": None,              # backup — esprieaether_24_7.bat + git push
    "secrux": None,                # security scans — aether-security agent
    "vito": None,                  # VPS deploy — cloud_desktop_agent tunnel
}

# known stack ports (what we map)
STACK_PORTS = {
    11434: "ollama", 11435: "router", 11436: "orchestrator",
    5000: "web", 5001: "cloud-desktop", 5100: "sunna-api",
    5101: "dsh-bridge", 5102: "integrations", 5103: "kanban", 5104: "homedock", 8000: "jarvis",
}


def port_open(p: int, host: str = "127.0.0.1", t: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, p), timeout=t):
            return True
    except Exception:
        return False


def stack_languages(d: Path) -> list:
    langs = set()
    for pat, lang in [("*.py", "python"), ("*.ts", "typescript"), ("*.go", "go"),
                      ("package.json", "node"), ("*.rs", "rust"), ("Dockerfile", "docker")]:
        if list(d.rglob(pat))[:1]:
            langs.add(lang)
    return sorted(langs)


@app.route("/")
def root():
    return """<h1>🔌 Integrations</h1><p>list: <a href="/list">/list</a> · scan: <a href="/scan">/scan</a> · health: <a href="/health">/health</a></p>"""


@app.route("/health")
def health():
    return jsonify({"status": "ok", "integrations_dir": str(INT_DIR)})


@app.route("/list")
def list_all():
    out = []
    for name, (repo, role, prio, use) in CATALOG.items():
        d = INT_DIR / name
        linked = d.exists() and len(list(d.iterdir())) > 0 if d.exists() else False
        folded = name in FOLDED_SERVICES
        # folded kanban/homedock are linked if their service is up
        if name == "veritas-kanban":
            linked = linked or port_open(5103)
        elif name == "homedock":
            linked = linked or port_open(5104)
        elif name == "invoice-builder":
            # folded: devis + facture builders exist
            linked = True
        elif name in ("hypit", "dozzle", "runtipi", "mini-qr", "gobackup", "secrux", "vito"):
            # folded: native equivalent in-stack
            linked = True
        out.append({
            "name": name, "repo": repo, "role": role, "priority": prio,
            "use": use, "linked": linked, "folded": folded,
            "languages": stack_languages(d) if linked and d.exists() else (["folded"] if folded else []),
        })
    return jsonify({"integrations": out, "total": len(out),
                    "linked": sum(1 for o in out if o["linked"])})


@app.route("/scan")
def scan():
    """Live port map (Portracker-style) + service health (Checkmate-style)."""
    ports = {str(p): {"name": n, "up": port_open(p)} for p, n in STACK_PORTS.items()}
    # public site
    site_up = False
    try:
        urllib.request.urlopen("https://silly-belekoy-aa2bf7.netlify.app/", timeout=6)
        site_up = True
    except urllib.error.HTTPError as e:
        site_up = e.code in (401, 403)
    except Exception:
        site_up = False
    return jsonify({"ports": ports, "site_up": site_up,
                    "up_count": sum(1 for v in ports.values() if v["up"])})


@app.route("/status/<name>")
def one(name):
    d = INT_DIR / name
    if not d.exists():
        return jsonify({"linked": False, "name": name}), 404
    files = [f.name for f in d.iterdir() if f.is_file()][:15]
    if name in CATALOG:
        repo, role, prio, use = CATALOG[name]
    else:
        repo = role = prio = use = None
    return jsonify({"linked": True, "name": name, "languages": stack_languages(d),
                    "files": files,
                    "repo": repo, "role": role, "priority": prio, "use": use})


if __name__ == "__main__":
    print(f"🧩 Integrations adapter — {len(CATALOG)} catalog — port {PORT}")
    linked = sum(1 for n in CATALOG if (INT_DIR / n).exists() and list((INT_DIR / n).iterdir()))
    print(f"   linked: {linked}/{len(CATALOG)}")
    app.run(host="127.0.0.1", port=PORT, threaded=True)
