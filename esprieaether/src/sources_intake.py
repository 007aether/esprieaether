"""J93 — dépôt de sources documentaires réelles, tracées localement.

Ce module ne rédige aucun contenu juridique, fiscal ou social : il copie
un fichier fourni par l'utilisateur, calcule son empreinte et enregistre
une provenance locale. Les modèles, README et fichiers vides sont refusés,
comme dans ``robot_engine._has_real_source``.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_ROOT = BASE_DIR / "data" / "sources"
PROVENANCE_PATH = BASE_DIR / "state" / "sources_intake.jsonl"

CATEGORIES = ("legal", "fiscal", "travail")
TEMPLATE_PREFIXES = ("_", "README", ".")
MIN_BYTES = 8
_UNSAFE = re.compile(r"[^\w.\-]+", re.UNICODE)


def _name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).strip()
    safe = _UNSAFE.sub("_", normalized).strip("._")[:120]
    return safe or "source.txt"


def ingest(
    source: Union[str, Path],
    category: str,
    *,
    root: Union[str, Path] = DATA_ROOT,
    provenance_path: Union[str, Path] = PROVENANCE_PATH,
) -> dict:
    """Copie une vraie pièce dans ``root/category`` et trace son empreinte."""
    if category not in CATEGORIES:
        raise ValueError("category_not_allowed")
    src = Path(source)
    if not src.is_file():
        raise ValueError("source_not_found")
    if src.name.startswith(TEMPLATE_PREFIXES):
        raise ValueError("template_not_a_source")
    payload = src.read_bytes()
    if len(payload) < MIN_BYTES:
        raise ValueError("empty_source")

    folder = Path(root) / category
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / _name(src.name)
    if destination.exists():
        if destination.read_bytes() != payload:
            raise ValueError("destination_conflict")
    else:
        destination.write_bytes(payload)

    digest = hashlib.sha256(payload).hexdigest()
    entry = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "category": category,
        "sourceName": _name(src.name),
        "destination": str(destination),
        "sha256": digest,
        "bytes": len(payload),
    }
    trail = Path(provenance_path)
    trail.parent.mkdir(parents=True, exist_ok=True)
    with trail.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Copie une pièce réelle fournie par l'utilisateur sans rien inventer.")
    parser.add_argument("source", help="chemin du fichier à déposer")
    parser.add_argument("category", choices=CATEGORIES, help="legal, fiscal ou travail")
    args = parser.parse_args()
    print(json.dumps(ingest(args.source, args.category), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


__all__ = ["CATEGORIES", "DATA_ROOT", "PROVENANCE_PATH", "ingest"]
