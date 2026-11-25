"""J76/C1 — actions proposées par le modèle, jamais exécutées sans décision explicite.

États: proposed → approved_once|denied → executed|failed.
Le journal local est écrit en JSONL avec les mêmes transitions. Aucune commande
n'est lancée ici : ce module ne fait que proposer, décider et tracer.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(BASE_DIR, "state", "action_requests.json")
AUDIT_PATH = os.path.join(BASE_DIR, "state", "action_audit.jsonl")

STATES = ("proposed", "approved_once", "denied", "executed", "failed")
DECISIONS = ("approved_once", "denied")
OUTCOMES = ("executed", "failed")
MAX_FIELD_CHARS = 200
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|token|password|secret|authorization|bearer)\s*[=:]\s*\S+"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _scrub(value: object) -> str:
    """Supprime la valeur d'un secret sans conserver le nom du champ."""
    return _SECRET_ASSIGNMENT.sub("[redacted]", str(value or ""))[:MAX_FIELD_CHARS]


class ActionRequests:
    def __init__(self, state_path: str = STATE_PATH, audit_path: str = AUDIT_PATH) -> None:
        self.state_path = str(state_path)
        self.audit_path = str(audit_path)

    def _load(self) -> List[Dict[str, object]]:
        try:
            with open(self.state_path, "r", encoding="utf-8") as handle:
                rows = json.load(handle)
            return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
        except (OSError, ValueError):
            return []

    def _save(self, rows: List[Dict[str, object]]) -> None:
        folder = os.path.dirname(self.state_path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as handle:
            json.dump(rows[:200], handle, ensure_ascii=False, indent=2)

    def _audit(self, item: Dict[str, object], previous: Optional[str],
               new: str, actor: str, detail: str = "") -> None:
        folder = os.path.dirname(self.audit_path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        entry = {
            "at": _now(),
            "id": str(item.get("id") or ""),
            "from": previous,
            "to": new,
            "actor": _scrub(actor),
            "detail": _scrub(detail),
        }
        with open(self.audit_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def propose(self, action: str, target: str = "", reason: str = "",
                source: str = "voice") -> Dict[str, object]:
        item = {
            "id": "act-" + uuid.uuid4().hex[:10],
            "action": _scrub(action),
            "target": _scrub(target),
            "reason": _scrub(reason),
            "source": _scrub(source),
            "status": "proposed",
            "createdAt": _now(),
            "decidedAt": None,
            "decidedBy": None,
            "receipt": None,
        }
        rows = self._load()
        rows.append(item)
        self._save(rows)
        self._audit(item, None, "proposed", source, item["action"])
        return dict(item)

    def _find(self, action_id: str) -> Dict[str, object]:
        for row in self._load():
            if str(row.get("id")) == str(action_id):
                return row
        raise ValueError("action_not_found")

    def decide(self, action_id: str, decision: str,
               decided_by: str = "hud") -> Dict[str, object]:
        if decision not in DECISIONS:
            raise ValueError("invalid_decision")
        rows = self._load()
        row = next((r for r in rows if str(r.get("id")) == str(action_id)), None)
        if row is None or row.get("status") != "proposed":
            raise ValueError("invalid_transition")
        previous = str(row.get("status"))
        row["status"] = decision
        row["decidedAt"] = _now()
        row["decidedBy"] = _scrub(decided_by)
        self._save(rows)
        self._audit(row, previous, decision, decided_by, "")
        return dict(row)

    def finish(self, action_id: str, status: str, receipt: str = "") -> Dict[str, object]:
        if status not in OUTCOMES:
            raise ValueError("invalid_outcome")
        row = self._find(action_id)
        if row.get("status") != "approved_once":
            raise ValueError("invalid_transition")
        previous = str(row.get("status"))
        row["status"] = status
        row["receipt"] = _scrub(receipt)
        self._save([row if str(r.get("id")) == str(action_id) else r for r in self._load()])
        self._audit(row, previous, status, "local-run", receipt)
        return dict(row)

    def public(self, limit: int = 20) -> List[Dict[str, object]]:
        keys = ("id", "action", "target", "reason", "source", "status",
                "createdAt", "decidedAt", "decidedBy")
        return [
            {key: _scrub(row.get(key)) if key in ("target", "reason") else row.get(key)
             for key in keys}
            for row in self._load()[:max(0, min(int(limit), 20))]
        ]


def ensure_state(state_path: str = STATE_PATH,
                 audit_path: str = AUDIT_PATH) -> ActionRequests:
    """Crée le dossier local vide au premier démarrage, sans jamais deviner d'action."""
    store = ActionRequests(state_path, audit_path)
    if not os.path.exists(store.state_path):
        store._save([])
    if not os.path.exists(store.audit_path):
        folder = os.path.dirname(store.audit_path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(store.audit_path, "a", encoding="utf-8"):
            pass
    return store


def default_store() -> ActionRequests:
    return ensure_state(STATE_PATH, AUDIT_PATH)


__all__ = ["ActionRequests", "DECISIONS", "OUTCOMES", "STATES",
           "ensure_state", "default_store"]
