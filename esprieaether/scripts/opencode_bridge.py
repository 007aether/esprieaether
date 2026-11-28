#!/usr/bin/env python3
"""J174 — côté OpenCode du pont de fichiers local avec Atulya.

Aucun réseau, aucune clé, aucun secret : Atulya écrit une question dans
``state/opencode_bridge/questions.jsonl`` ; OpenCode écrit sa réponse dans
``answers.jsonl``. Atulya ne la restitue que si le fichier contient réellement
une réponse (aucune réponse inventée).

Usage :
  python scripts/opencode_bridge.py pending
  python scripts/opencode_bridge.py answer q-12345678 "texte de la réponse"
  python scripts/opencode_bridge.py inbox
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from pc_gateway import _scrub  # noqa: E402

DEFAULT_DIR = Path(__file__).resolve().parents[1] / "state" / "opencode_bridge"


def _rows(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def pending(folder: Path = DEFAULT_DIR) -> list[dict]:
    """Questions sans réponse, dans l'ordre d'écriture."""
    folder = Path(folder)
    answered = {
        str(row.get("question_id"))
        for row in _rows(folder / "answers.jsonl")
        if str(row.get("text") or "").strip()
    }
    return [
        row for row in _rows(folder / "questions.jsonl")
        if row.get("kind") == "question" and str(row.get("id")) not in answered
    ]


def inbox(folder: Path = DEFAULT_DIR) -> list[dict]:
    """Dernières questions écrites par Atulya (10 maximum)."""
    return [row for row in _rows(Path(folder) / "questions.jsonl")
            if row.get("kind") == "question"][-10:]


def answer(question_id: str, text: str, folder: Path = DEFAULT_DIR) -> dict:
    """Écrit une réponse datée ; échoue sur un identifiant ou texte vide."""
    question_id = str(question_id or "").strip()
    clean = _scrub(str(text or "").strip())[:800]
    if not question_id.startswith("q-") or not clean:
        raise ValueError("identifiant de question invalide ou réponse vide")
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    row = {
        "kind": "answer",
        "question_id": question_id,
        "text": clean,
        "answeredBy": "opencode",
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    with (folder / "answers.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", default=str(DEFAULT_DIR), help="dossier partagé")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("pending")
    sub.add_parser("inbox")
    write = sub.add_parser("answer")
    write.add_argument("question_id")
    write.add_argument("text")
    args = parser.parse_args(argv)
    folder = Path(args.dir)
    if args.command == "answer":
        row = answer(args.question_id, args.text, folder)
        print(json.dumps(row, ensure_ascii=False))
    else:
        rows = pending(folder) if args.command == "pending" else inbox(folder)
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
