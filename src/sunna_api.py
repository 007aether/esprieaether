#!/usr/bin/env python3
"""
sunna_api.py — Sunna ⇄ EsprieAether bridge

Reads the Sunna company workspace (bots, research, catalogue, coordination)
and exposes it as a JSON API on port 5100, so the EsprieAether control
center (and any other service) can see the company's state in one place.

Endpoints:
  GET  /health           — bridge alive
  GET  /status           — full company snapshot (products, agents, bots, docs)
  GET  /bots             — the 5 Sunna bots + last-run info
  GET  /research         — the 7 research agents + their files
  GET  /catalogue        — products (from Catalogue/)
  GET  /coordination     — HANDOFF.md + last Hermes results
  GET  /bilans           — the daily bilan reports
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = Flask(__name__)

# ── CORS: /control page fetches this bridge cross-origin ──
@app.after_request
def _cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return resp

PORT = int(os.getenv("SUNNA_API_PORT", "5100"))
SUNNA = Path(os.getenv("SUNNA_DIR", str(Path.home() / "Desktop" / "Sunna-Equipe-Industrial")))


def _p(*parts) -> Path:
    return SUNNA.joinpath(*parts)


def _read_text(p: Path, limit: int = 8000) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")[:limit]
    except Exception:
        return ""


def _list_files(d: Path, exts=(".md", ".txt", ".json", ".html", ".docx", ".xlsx", ".pdf", ".png", ".jpg")) -> list:
    out = []
    if not d.exists():
        return out
    for f in sorted(d.rglob("*")):
        if f.is_file() and f.suffix.lower() in exts:
            try:
                st = f.stat()
                out.append({
                    "name": f.name,
                    "path": str(f.relative_to(SUNNA)),
                    "size": st.st_size,
                    "modified": datetime.fromtimestamp(st.st_mtime, timezone.utc).strftime("%Y-%m-%d %H:%M"),
                })
            except Exception:
                pass
    return out


# ── Endpoints ──

@app.route("/")
def root():
    return """<h1>☀️ Sunna API</h1><p>status: <a href="/status">/status</a> · bots: <a href="/bots">/bots</a> · health: <a href="/health">/health</a></p>"""


@app.route("/health")
def health():
    return jsonify({"status": "ok", "sunna_dir": str(SUNNA), "exists": SUNNA.exists()})


@app.route("/status")
def status():
    return jsonify({
        "company": {
            "name": "SUNNA ÉQUIPE INDUSTRIAL",
            "type": "SARL AU",
            "ice": "004054044000074",
            "neg_cert": "3304417",
            "capital": "40,000 MAD",
            "activity": "تصنيع منتجات معدنية · حدادة · غلفنة · هياكل",
            "workshop": "72م² — الدار البيضاء",
            "phone": "0770720602",
        },
        "team": {
            "amine": {"role": "مؤسس — قرارات · فلوس · زبناء", "status": "field"},
            "sunna": {"role": "مستشار تقني", "status": "active"},
            "hermes": {"role": "وكيل خارجي", "status": "active"},
            "agents": ["A1 غلفنة", "A2 أثمنة", "A3 مخططات", "A4 قانوني", "M1 سوق", "L1 ضرائب", "L2 شغل"],
            "bots": ["Veille", "Al_Afdal", "Souk", "Offres", "Pinterest"],
        },
        "counts": {
            "research_files": len(_list_files(_p("Recherche"))),
            "docs": len(_list_files(_p("Dossier_Charika"))),
            "catalogue": len(_list_files(_p("Catalogue"))),
            "assets": len(_list_files(_p("Assets"))),
            "bots": len(_list_files(_p("bots"))),
        },
    })


@app.route("/bots")
def bots():
    out = []
    bot_dir = _p("bots")
    schedules = {
        "veille_bot.py": "كل 6 ساعات — رصد 187 مستودع",
        "al_afdal.py": "يومياً 07:30 — تقرير شامل",
        "souk_bot.py": "يومياً 08:30 — أثمنة المواد والسوق",
        "offres_bot.py": "يومياً 09:00 — المباريات والفرص",
        "pinterest_bot.py": "اثنين 09:15 — أفكار وتصاور",
    }
    for f in _list_files(bot_dir, exts=(".py",)):
        out.append({
            "name": f["name"],
            "schedule": schedules.get(f["name"], "غير مجدول"),
            "modified": f["modified"],
            "size": f["size"],
        })
    return jsonify({"bots": out, "cmd_scripts": [f["name"] for f in _list_files(bot_dir, exts=(".cmd",))]})


@app.route("/research")
def research():
    files = _list_files(_p("Recherche"))
    agents = {
        "A1_Galvanisation.md": "الغلفنة — 9 شركات",
        "A2_Prix.md": "الأثمنة — 8 بنود",
        "A3_Plans.md": "المخططات — 4 منتجات",
        "A4_Legal.md": "القانوني",
        "M1_Marche_Metallerie.md": "السوق — 777 سطر",
        "L1_Fiscalite_Exonerations.md": "الضرائب — 573 سطر",
        "L2_Travail_SMIG_Societe.md": "الشغل — 779 سطر",
    }
    out = []
    for f in files:
        out.append({
            "file": f["name"],
            "purpose": agents.get(f["name"], ""),
            "size": f["size"],
            "modified": f["modified"],
            "path": f["path"],
        })
    return jsonify({"agents": out})


@app.route("/catalogue")
def catalogue():
    cat = _p("Catalogue")
    return jsonify({
        "files": _list_files(cat),
        "index_excerpt": _read_text(cat / "_index.txt", 2000),
    })


@app.route("/coordination")
def coordination():
    handoff = _p("Coordination", "HANDOFF.md")
    results_dir = _p("Coordination", "hermes_results")
    results = []
    if results_dir.exists():
        for f in sorted(results_dir.glob("*.md"), reverse=True)[:10]:
            st = f.stat()
            results.append({
                "name": f.name,
                "size": st.st_size,
                "modified": datetime.fromtimestamp(st.st_mtime, timezone.utc).strftime("%Y-%m-%d %H:%M"),
                "path": str(f.relative_to(SUNNA)),
            })
    return jsonify({
        "handoff": _read_text(handoff, 3000),
        "hermes_results": results,
    })


@app.route("/bilans")
def bilans():
    out = []
    for f in _list_files(SUNNA, exts=(".md",)):
        if "bilan" in f["name"].lower() or "etat_du_projet" in f["name"].lower():
            out.append(f)
    return jsonify({"bilans": out})


@app.route("/netlify")
def netlify():
    """Sunna live site URL + claim status."""
    nf = SUNNA / "Coordination" / "netlify_url.json"
    if not nf.exists():
        return jsonify({"deployed": False})
    try:
        return jsonify({"deployed": True, **json.loads(nf.read_text(encoding="utf-8"))})
    except Exception:
        return jsonify({"deployed": False})


@app.route("/prices")
def prices():
    """Live material prices (steel/galva/zinc) from the price tracker."""
    pj = SUNNA / "Recherche" / "live_prices.json"
    if not pj.exists():
        return jsonify({"tracked": False})
    try:
        return jsonify({"tracked": True, "prices": json.loads(pj.read_text(encoding="utf-8"))})
    except Exception:
        return jsonify({"tracked": False})


if __name__ == "__main__":
    print(f"📋 Sunna API bridge — {SUNNA} — port {PORT}")
    print(f"   sunna dir exists: {SUNNA.exists()}")
    app.run(host="127.0.0.1", port=PORT, threaded=True)
