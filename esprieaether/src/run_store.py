"""J53 — journal d'exécution local, stdlib uniquement.

Toute action du JARVIS passe par un état terminal. Aucune écriture ne contient
de secret : `redact()` masque les affectations de clés/tokens/mots de passe.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import sqlite3
from typing import Dict, List, Optional

TERMINAL_STATUSES = ("succeeded", "failed", "timed_out", "cancelled")
VALID_STATUSES = TERMINAL_STATUSES + ("running",)

_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|token|password|secret|authorization|bearer)\s*[=:]\s*\S+"
)


def redact(text: str) -> str:
    """Masque les valeurs de secrets sans lire ni conserver le secret original."""
    if not text:
        return ""
    return _SECRET_ASSIGNMENT.sub(lambda m: f"{m.group(1)}=<redacted>", str(text))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class RunStore:
    def __init__(self, db_path):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.path))
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    action      TEXT NOT NULL,
                    actor       TEXT NOT NULL,
                    status      TEXT NOT NULL,
                    detail      TEXT NOT NULL DEFAULT '',
                    mode        TEXT NOT NULL DEFAULT 'full_local',
                    request_id  TEXT,
                    tainted     INTEGER NOT NULL DEFAULT 0,
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_runs_status_updated "
                "ON runs(status, updated_at)"
            )
            conn.commit()
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _row(row: Optional[sqlite3.Row]) -> Optional[Dict[str, object]]:
        if row is None:
            return None
        data = dict(row)
        data["tainted"] = bool(data.get("tainted"))
        return data

    def record(
        self,
        action: str,
        *,
        actor: str,
        status: str = "running",
        detail: str = "",
        mode: str = "full_local",
        request_id: Optional[str] = None,
        tainted: bool = False,
    ) -> int:
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid_status:{status}")
        now = _now()
        conn = self._connect()
        try:
            cur = conn.execute(
                "INSERT INTO runs (action, actor, status, detail, mode, "
                "request_id, tainted, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    str(action), str(actor), status, redact(detail), str(mode),
                    request_id, int(bool(tainted)), now, now,
                ),
            )
            conn.commit()  # écriture avant toute notification
            return int(cur.lastrowid)
        finally:
            conn.close()

    def update(self, run_id: int, status: str, detail: Optional[str] = None) -> bool:
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid_status:{status}")
        conn = self._connect()
        try:
            if detail is None:
                cur = conn.execute(
                    "UPDATE runs SET status=?, updated_at=? WHERE id=?",
                    (status, _now(), run_id),
                )
            else:
                cur = conn.execute(
                    "UPDATE runs SET status=?, detail=?, updated_at=? WHERE id=?",
                    (status, redact(detail), _now(), run_id),
                )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def get(self, run_id: int) -> Optional[Dict[str, object]]:
        conn = self._connect()
        try:
            return self._row(
                conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            )
        finally:
            conn.close()

    def list_runs(self, limit: int = 50) -> List[Dict[str, object]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY id DESC LIMIT ?", (max(1, int(limit)),)
            ).fetchall()
            return [self._row(r) for r in rows]  # type: ignore[misc]
        finally:
            conn.close()

    def reap_stale(self, timeout_seconds: int = 300) -> int:
        """Aucune tâche ne reste 'running' indéfiniment : elle devient timed_out."""
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)).isoformat(
            timespec="seconds"
        )
        conn = self._connect()
        try:
            cur = conn.execute(
                "UPDATE runs SET status='timed_out', detail=?, updated_at=? "
                "WHERE status='running' AND updated_at <= ?",
                ("reaped:no_terminal_state", _now(), cutoff),
            )
            conn.commit()
            return int(cur.rowcount)
        finally:
            conn.close()

    def export_json(self, path, limit: int = 50) -> Dict[str, object]:
        """Exporte uniquement les champs publics pour le dashboard local."""
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        runs = []
        for row in self.list_runs(limit):
            runs.append({
                "id": row["id"],
                "action": row["action"],
                "actor": row["actor"],
                "status": row["status"],
                "createdAt": row["created_at"],
            })
        payload = {
            "generatedAt": _now(),
            "available": True,
            "source": "run_ledger.db",
            "stats": self.stats(),
            "runs": runs,
        }
        tmp = destination.with_suffix(destination.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(destination)
        return payload

    def stats(self) -> Dict[str, int]:
        conn = self._connect()
        try:
            counts = {
                row["status"]: row["n"]
                for row in conn.execute(
                    "SELECT status, COUNT(*) AS n FROM runs GROUP BY status"
                ).fetchall()
            }
        finally:
            conn.close()
        result = {status: int(counts.get(status, 0)) for status in VALID_STATUSES}
        result["total"] = sum(result.values())
        return result


__all__ = ["RunStore", "TERMINAL_STATUSES", "VALID_STATUSES", "redact"]
