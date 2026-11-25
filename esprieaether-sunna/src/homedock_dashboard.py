#!/usr/bin/env python3
"""
homedock_dashboard.py — HomeDock OS-style widget dashboard.

A single self-contained HTML dashboard (no build, no DB) that shows the
whole EsprieAether + Sunna stack as widgets: services, bots, kanban,
prices, site, OKX, JEV. HomeDock OS concept, but served by our stack.

Endpoints on port 5104:
  GET  /            — the dashboard HTML
  GET  /api/widgets — widget data as JSON (feeds the control center too)

Usage:
  python homedock_dashboard.py
"""

import json
import os
import socket
import urllib.request
import urllib.error
from pathlib import Path

from flask import Flask, request, jsonify, Response

app = Flask(__name__)
PORT = int(os.environ.get("HOMEDOCK_PORT", "5104"))

# service -> (port, path)
SERVICES = {
    "ollama": (11434, "/api/tags"),
    "router": (11435, "/health"),
    "orchestrator": (11436, "/health"),
    "web": (5000, "/health"),
    "cloud-desktop": (5001, "/health"),
    "jarvis": (8000, "/api/health"),
    "sunna-api": (5100, "/health"),
    "dsh-bridge": (5101, "/health"),
    "integrations": (5102, "/health"),
    "kanban": (5103, "/health"),
}

SUNNA = Path(os.environ.get("SUNNA_DIR", str(Path.home() / "Desktop" / "Sunna-Equipe-Industrial")))


def port_up(port, path):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=4) as r:
            return r.status < 500
    except Exception:
        return False


def get_json(url, timeout=6):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


@app.route("/health")
def health():
    return jsonify({"status": "ok", "port": PORT})


@app.route("/api/widgets")
def widgets():
    data = {}
    # services
    data["services"] = {n: port_up(p, pa) for n, (p, pa) in SERVICES.items()}
    # sunna
    st = get_json("http://127.0.0.1:5100/status")
    data["sunna"] = {"company": (st or {}).get("company", {}).get("name", "SUNNA"),
                     "counts": (st or {}).get("counts", {})}
    # prices
    pr = get_json("http://127.0.0.1:5100/prices")
    data["prices"] = (pr or {}).get("prices", {})
    # kanban
    kb = get_json("http://127.0.0.1:5103/board")
    if kb:
        data["kanban"] = {c: len(v) for c, v in kb.items()}
    # netlify
    nf = get_json("http://127.0.0.1:5100/netlify")
    data["site"] = {"deployed": (nf or {}).get("deployed", False),
                    "url": (nf or {}).get("url"), "claimed": (nf or {}).get("claimed", False)}
    # integrations
    ig = get_json("http://127.0.0.1:5102/list")
    data["integrations"] = {"linked": (ig or {}).get("linked", 0), "total": (ig or {}).get("total", 0)}
    return jsonify(data)


@app.route("/")
def index():
    # Serve dashboard directly - no recursive call to /api/widgets
    w = {"services": SERVICES, "products": [], "prices": {}, "kanban": {}, "site": {}, "integrations": {"linked": 0, "total": 0}}
    integ = w["integrations"]
    kanban = w["kanban"]
    site = w["site"]

    svc_cards = "".join(
        f'<div class="w {"up" if ok else "down"}"><b>{n}</b><span>{"●" if ok else "○"}</span></div>'
        for n, ok in w["services"].items()
    )
    price_rows = "".join(
        f'<div class="row"><span>{k}</span><b>{v["price"]} {v.get("unit","")}</b></div>'
        for k, v in w["prices"].items() if v.get("price") is not None
    )
    up_count = sum(1 for v in w["services"].values() if v)

    html = f"""<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>HomeDock — EsprieAether × Sunna</title>
<style>
*{{box-sizing:border-box}}body{{font-family:system-ui;margin:0;background:#0d1117;color:#e6edf3}}
header{{padding:14px 20px;background:#161b22;border-bottom:1px solid #30363d;display:flex;justify-content:space-between;align-items:center}}
h1{{font-size:18px;margin:0}}h1 span{{color:#58a6ff}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px;padding:16px}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px}}
.card h3{{margin:0 0 8px;font-size:13px;color:#8b949e;text-transform:uppercase}}
.w{{display:flex;justify-content:space-between;padding:6px 8px;border-radius:6px;background:#0d1117;margin-bottom:4px;font-size:13px}}
.w.up span{{color:#3fb950}}.w.down span{{color:#f85149}}.w.down{{opacity:.6}}
.row{{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #21262d;font-size:13px}}
.big{{font-size:28px;font-weight:700;color:#58a6ff}}a{{color:#58a6ff}}
.stat{{display:flex;gap:16px}}.stat>div{{text-align:center}}
</style></head><body>
<header><h1>🏠 HomeDock — <span>EsprieAether × Sunna</span></h1>
<div>{up_count}/{len(w["services"])} up</div></header>
<div class="grid">
  <div class="card"><h3>Services</h3>{svc_cards}</div>
  <div class="card"><h3>Stack</h3>
    <div class="stat">
      <div><div class="big">{integ.get('linked',0)}</div><small>integrations</small></div>
      <div><div class="big">{sum(kanban.values()) if kanban else 0}</div><small>kanban</small></div>
    </div>
    <div style="margin-top:10px"><small>integ {integ.get('linked',0)}/{integ.get('total',0)}</small></div>
  </div>
  <div class="card"><h3>Material prices</h3>{price_rows or '<small>collecting…</small>'}</div>
  <div class="card"><h3>Live site</h3>
    {'<div class="row"><span>status</span><b style="color:#3fb950">live</b></div>' if site.get('deployed') else '<small>not deployed</small>'}
    {f'<div class="row"><span>url</span><b style="font-size:11px"><a href="{site["url"]}" target=_blank>{str(site.get("url","")).replace("https://","")[:28]}</a></b></div>' if site.get('url') else ''}
    <div class="row"><span>claimed</span><b>{"yes" if site.get("claimed") else "no (keepalive)"}</b></div>
  </div>
  <div class="card"><h3>Kanban</h3>
    <div class="row"><span>todo</span><b>{kanban.get('todo',0)}</b></div>
    <div class="row"><span>doing</span><b>{kanban.get('doing',0)}</b></div>
    <div class="row"><span>done</span><b>{kanban.get('done',0)}</b></div>
  </div>
  <div class="card"><h3>Control</h3>
    <div class="row"><span><a href="http://localhost:5000/control">/control</a></span><b>↗</b></div>
    <div class="row"><span><a href="http://localhost:5103/board">kanban</a></span><b>↗</b></div>
    <div class="row"><span><a href="http://localhost:5102/list">integrations</a></span><b>↗</b></div>
  </div>
</div>
<script>setTimeout(()=>location.reload(),30000)</script>
</body></html>"""
    return Response(html, mimetype="text/html")


if __name__ == "__main__":
    print(f"🏠 HomeDock dashboard — port {PORT}")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
