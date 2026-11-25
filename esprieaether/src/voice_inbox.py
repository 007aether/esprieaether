"""J62 — boîte de réception vocale locale, stdlib uniquement.

Chaque tournée est écrite en JSONL (une ligne par tour) dans ``state/`` pour
que l'agent puisse lire ce qui a été dit et y répondre. Les valeurs sont
filtrées et masquées avec ``run_store.redact`` : aucun secret n'est conservé.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import run_store

BASE_DIR = Path(__file__).resolve().parents[1]
INBOX_PATH = BASE_DIR / "state" / "voice_inbox.jsonl"
LATEST_PATH = BASE_DIR / "state" / "voice_latest.txt"
MAX_BYTES = 1_000_000
FIELDS = ("ok", "heard", "reply", "spoken", "language", "engine", "model", "reason", "source")


class VoiceInbox:
    def __init__(self, path=INBOX_PATH, latest=LATEST_PATH):
        self.path = Path(path)
        self.latest = Path(latest)

    def append(self, record: Dict[str, object]) -> Dict[str, object]:
        data: Dict[str, object] = {}
        for key in FIELDS:
            if key not in record:
                continue
            value = record.get(key)
            data[key] = run_store.redact(value) if isinstance(value, str) else value
        data["ts"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(data, ensure_ascii=False) + "\n")
        self._rotate()
        self.latest.parent.mkdir(parents=True, exist_ok=True)
        heard = str(data.get("heard") or "")[:160]
        reply = str(data.get("reply") or "")[:240]
        self.latest.write_text(
            f"{data['ts']} | ok={data.get('ok')} | heard={heard}\nreply={reply}\n",
            encoding="utf-8",
        )
        return data

    def read(self, limit: int = 20) -> List[Dict[str, object]]:
        if not self.path.exists():
            return []
        rows = []
        for line in self.path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                item = json.loads(line)
            except (ValueError, TypeError):
                continue
            if isinstance(item, dict):
                rows.append(item)
        count = max(1, int(limit))
        return rows[-count:]

    def _rotate(self) -> None:
        try:
            if self.path.stat().st_size <= MAX_BYTES:
                return
            backup = self.path.with_suffix(self.path.suffix + ".1")
            backup.write_bytes(self.path.read_bytes())
            self.path.write_text("", encoding="utf-8")
        except OSError:  # pragma: no cover - disque plein / permissions
            pass


def probe() -> Dict[str, object]:
    """Capacités publiques de la boîte : aucun secret, aucun contenu vocal."""
    return {
        "available": True,
        "mode": "local_jsonl",
        "path": str(INBOX_PATH),
        "fields": list(FIELDS),
        "reason": None,
    }


__all__ = ["INBOX_PATH", "LATEST_PATH", "FIELDS", "VoiceInbox", "probe"]
