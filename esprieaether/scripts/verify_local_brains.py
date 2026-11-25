#!/usr/bin/env python3
"""Vérification de bout en bout après téléchargement des 3 GGUF locaux.

Tout est en lecture seule : aucun secret affiché, aucun .env modifié.
Écrit seulement state/local_brain_verification.json (rapport horodaté).
"""

import json
import sqlite3
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ROUTER = "http://127.0.0.1:31416"
GATEWAY = "http://127.0.0.1:5001"
DB = Path(r"C:\Users\aether\ESPRIEAETHER\data\esprieaether.db")
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get(url, timeout=20):
    with OPENER.open(url, timeout=timeout) as resp:
        return json.loads(resp.read())


def post(url, payload, timeout=240):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with OPENER.open(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def main():
    report = {"checked_at": datetime.now(timezone.utc).isoformat()}

    health = get(ROUTER + "/health")
    report["router_health"] = health
    models = get(ROUTER + "/v1/models")
    report["router_models"] = [m["id"] for m in models.get("data", [])]

    if health.get("count", 0) > 0:
        model = health["available"][0]
        answer = post(ROUTER + "/v1/chat/completions", {
            "model": model,
            "messages": [{"role": "user", "content": "Réponds uniquement PONG."}],
            "max_tokens": 16,
        })
        report["router_completion"] = {
            "model": model,
            "text": answer["choices"][0]["message"]["content"][:120],
        }
    else:
        report["router_completion"] = "skipped: no complete GGUF"

    report["gateway_status"] = get(GATEWAY + "/llm/status")
    chat = post(GATEWAY + "/chat/completions", {
        "prompt": "Réponds uniquement PONG.",
        "max_tokens": 16,
    })
    report["gateway_completion"] = {
        "routed_via": chat.get("routed_via"),
        "status": chat.get("status"),
    }

    if DB.exists():
        conn = sqlite3.connect(DB)
        row = conn.execute(
            "SELECT status, summary, created_at FROM robot_results "
            "WHERE robot_id='SYS_01' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        report["sentinel"] = row
    else:
        report["sentinel"] = "db introuvable"

    out = BASE / "state" / "local_brain_verification.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("REPORT=" + str(out))


if __name__ == "__main__":
    main()
