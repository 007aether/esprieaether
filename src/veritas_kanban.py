#!/usr/bin/env python3
"""
veritas_kanban.py — markdown kanban board for Sunna + EsprieAether.

Veritas-Kanban-style board, but plain files (no DB, no server).
Reads/writes `Coordination/kanban.md` — columns: todo / doing / done.

Endpoints on port 5103:
  GET  /board          — the board as JSON (parsed from kanban.md)
  POST /add            — {"title": "...", "col": "todo", "tag": "..."}
  POST /move           — {"title": "...", "to": "doing"}
  GET  /health         — alive

Usage:
  python veritas_kanban.py           # serve on 5103
  python veritas_kanban.py --seed    # create starter board
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, request, jsonify

PORT = int(os.environ.get("KANBAN_PORT", "5103"))
KANBAN = Path(os.environ.get("SUNNA_DIR", str(Path.home() / "Desktop" / "Sunna-Equipe-Industrial"))) / "Coordination" / "kanban.md"

app = Flask(__name__)

COLS = ["todo", "doing", "done"]

SEED = """# 📋 Sunna Kanban

## todo
- [ ] 🔴 تاريخ الشهادة السلبية (90 يوم!) — Amine
- [ ] 🔴 ثمن الغلفنة — Galvafer 0522 67 46 31 — Amine
- [ ] 🔴 3 عروض أثمنة (devis) — Amine
- [ ] 🟡 اختيار اللوغو (F1/F3/F6/F10) — Amine
- [ ] 🟡 6 صور حقيقية (ورشة + منتجات + équipe) — Amine
- [ ] 🟢 GMB — business.google.com — Bot ready

## doing
- [ ] 🟢 Netlify site — live (keepalive 24/7)

## done
- [x] ✅ Netlify deploy + keepalive
- [x] ✅ PDF devis builder
- [x] ✅ Live price tracker (galva/zinc)
- [x] ✅ Telegram /sunna commands
- [x] ✅ SOP wiki
- [x] ✅ 12 integrations linked
"""


def _read() -> str:
    if not KANBAN.exists():
        KANBAN.parent.mkdir(exist_ok=True)
        KANBAN.write_text(SEED, encoding="utf-8")
    return KANBAN.read_text(encoding="utf-8")


def parse_board(text: str) -> dict:
    board = {c: [] for c in COLS}
    current = None
    for line in text.splitlines():
        m = re.match(r"^##\s+(\w+)", line.strip())
        if m and m.group(1).lower() in board:
            current = m.group(1).lower()
            continue
        item = re.match(r"^\s*-\s*\[([ xX])\]\s*(.+)", line)
        if item and current:
            done = item.group(1).lower() == "x"
            title = item.group(2).strip()
            board[current].append({"title": title, "done": done})
    return board


def write_board(board: dict) -> None:
    lines = ["# 📋 Sunna Kanban", ""]
    for c in COLS:
        lines.append(f"## {c}")
        for it in board[c]:
            mark = "x" if it["done"] else " "
            lines.append(f"- [{mark}] {it['title']}")
        lines.append("")
    KANBAN.parent.mkdir(exist_ok=True)
    KANBAN.write_text("\n".join(lines), encoding="utf-8")


@app.route("/")
def root():
    return """<h1>📋 Veritas Kanban</h1><p>board: <a href="/board">/board</a> · health: <a href="/health">/health</a></p>"""


@app.route("/health")
def health():
    return jsonify({"status": "ok", "board": str(KANBAN)})


@app.route("/board")
def board():
    return jsonify(parse_board(_read()))


@app.route("/add", methods=["POST"])
def add():
    d = request.get_json(silent=True) or {}
    title = d.get("title", "").strip()
    col = d.get("col", "todo")
    if not title or col not in COLS:
        return jsonify({"error": "need title + valid col"}), 400
    board = parse_board(_read())
    board[col].append({"title": title, "done": col == "done"})
    write_board(board)
    return jsonify({"ok": True, "board": board})


@app.route("/move", methods=["POST"])
def move():
    d = request.get_json(silent=True) or {}
    title = d.get("title", "").strip()
    to = d.get("to", "")
    if not title or to not in COLS:
        return jsonify({"error": "need title + valid to"}), 400
    board = parse_board(_read())
    found = None
    for c in COLS:
        for it in board[c]:
            if title.lower() in it["title"].lower():
                found = (c, it)
                break
        if found:
            break
    if not found:
        return jsonify({"error": "item not found"}), 404
    board[found[0]].remove(found[1])
    it = found[1]
    it["done"] = (to == "done")
    board[to].append(it)
    write_board(board)
    return jsonify({"ok": True, "board": board})


if __name__ == "__main__":
    if "--seed" in sys.argv:
        KANBAN.parent.mkdir(exist_ok=True)
        KANBAN.write_text(SEED, encoding="utf-8")
        print(f"seeded: {KANBAN}")
    else:
        print(f"📋 Veritas-style kanban — {KANBAN} — port {PORT}")
        app.run(host="127.0.0.1", port=PORT, threaded=True)
