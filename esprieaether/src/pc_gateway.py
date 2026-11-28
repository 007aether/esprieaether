"""J171 — passerelle d'actions PC/Internet gouvernée par le propriétaire.

Le propriétaire a autorisé explicitement : Internet complet, exécution des
commandes qu'il écrit, et les trois modes de consentement (à chaque fois /
session / automatique). Cette passerelle n'accorde rien de plus : elle garde
les lignes rouges permanentes et trace chaque transition dans un audit local.

Aucun secret n'est lu ni conservé. Aucune action n'est inventée : le résultat
vient toujours de l'appel réel au navigateur ou au processus.
"""
from __future__ import annotations

import ipaddress
import json
import re
import subprocess
import uuid
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

_MODES = ("ask_each", "session", "auto")
_DECISIONS = ("approved_once", "denied")
_MAX_CHARS = 400

# Lignes rouges fixées par le propriétaire, valables même en mode automatique.
_RED_LINES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("touping_executable", re.compile(r"touping\.exe", re.I)),
    ("secret_file", re.compile(r"(?:^|[\s\\/])(?:\.env|\.npmrc|\.ssh[\s\\/])", re.I)),
    ("secret_assignment", re.compile(
        r"\b(?:api[_-]?key|token|password|secret|authorization|bearer)\s*[=:]\s*\S+", re.I)),
    ("phone_action", re.compile(
        r"\b(?:sms|send\s+sms|call\b|dial\b|adb\s+shell\s+am\s+start|tel:)", re.I)),
    ("destructive", re.compile(
        r"(?:\brm\s+-rf\b|\brmdir\s+/s\b|\bdel\s+/[fs]\b|\bformat\b|"
        r"Remove-Item\b[^\n]*-Recurse|Clear-RecycleBin\b)", re.I)),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _local_host(host: str) -> bool:
    name = host.strip().rstrip(".").lower()
    if not name or name in {"localhost", "localhost.localdomain"}:
        return True
    if name.endswith((".localhost", ".local", ".internal")):
        return True
    try:
        address = ipaddress.ip_address(name)
    except ValueError:
        return False
    return (address.is_loopback or address.is_private or address.is_link_local
            or address.is_multicast or address.is_reserved or address.is_unspecified)


def is_public_web_url(url: str) -> bool:
    """HTTPS/HTTP public avec requête autorisée (YouTube, recherche, etc.).

    Refuse boucle locale, réseau privé, identifiants et schemes hors HTTP(S).
    Contrairement à egress_guard.is_public_https_url, la query est autorisée :
    c'est nécessaire pour « شغّل راب مغربي » -> results?search_query=...
    """
    try:
        parts = urlsplit(str(url or "").strip())
    except ValueError:
        return False
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return False
    if parts.username or parts.password:
        return False
    return not _local_host(parts.hostname)


def _scrub(value: object) -> str:
    text = str(value or "")
    for _name, pattern in _RED_LINES:
        if pattern is _RED_LINES[2][1]:
            text = pattern.sub("[redacted]", text)
    return text[:_MAX_CHARS]


def _red_line(command: str) -> str | None:
    for name, pattern in _RED_LINES:
        if pattern.search(command or ""):
            return name
    return None


def _default_runner(command: str, timeout: int) -> dict:
    try:
        done = subprocess.run(
            command,
            shell=True,
            cwd=str(Path(__file__).resolve().parents[1]),
            capture_output=True,
            text=True,
            timeout=max(1, min(int(timeout), 120)),
            errors="replace",
        )
        return {
            "ok": done.returncode == 0,
            "stdout": _scrub(done.stdout),
            "stderr": _scrub(done.stderr),
            "code": done.returncode,
        }
    except Exception as exc:  # erreur réelle, pas un résultat inventé
        return {"ok": False, "stdout": "", "stderr": _scrub(str(exc)), "code": -1}


class PcGateway:
    def __init__(self, *, state_dir: str | Path | None = None,
                 browser_open: Callable[[str], object] | None = None,
                 runner: Callable[[str, int], dict] | None = None) -> None:
        root = Path(state_dir) if state_dir else Path(__file__).resolve().parents[1] / "state"
        root.mkdir(parents=True, exist_ok=True)
        self.state_dir = root
        self.state_path = root / "pc_action_last.json"
        self.audit_path = root / "pc_action_audit.jsonl"
        self.browser_open = browser_open or (lambda url: webbrowser.open_new_tab(url))
        self.runner = runner or _default_runner
        self.browser_calls: list[str] = []
        self.runner_calls: list[tuple[str, int]] = []
        self._plans: dict[str, dict] = {}
        self._session_grants: set[tuple[str, str]] = set()

    def _audit(self, row: dict, previous: str | None, new: str, actor: str) -> None:
        entry = {
            "at": _now(),
            "id": str(row.get("id") or ""),
            "kind": row.get("kind"),
            "target": _scrub(row.get("target")),
            "from": previous,
            "to": new,
            "actor": _scrub(actor),
            "status": new,
        }
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _write_last(self, row: dict) -> None:
        payload = {
            "id": row.get("id"),
            "kind": row.get("kind"),
            "target": _scrub(row.get("target")),
            "status": row.get("status"),
            "text": _scrub(row.get("text")),
            "executed": row.get("status") == "executed",
            "checkedAt": _now(),
        }
        tmp = self.state_path.with_name(self.state_path.name + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self.state_path)

    def last_result(self) -> dict:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"executed": False, "text": "ما كاينش نتيجة فعل محلي.", "status": "no_data_source"}

    def _execute(self, row: dict) -> dict:
        kind, target = row["kind"], row["target"]
        if kind == "open_url":
            self.browser_calls.append(target)
            self.browser_open(target)
            text = f"فتحت صفحة جديدة: {_scrub(target)}."
        elif kind == "run_command":
            self.runner_calls.append((target, 20))
            result = self.runner(target, 20)
            row["result"] = result
            out = str(result.get("stdout") or "").strip()
            err = str(result.get("stderr") or "").strip()
            text = (out or err or "الأمر ما رجّعش نص.")[:300]
            text = f"نفّذت الأمر: {text}"
        else:
            row["status"] = "refused"
            row["reason"] = "unknown_kind"
            row["text"] = "نوع الفعل غير معروف."
            return row
        row["status"] = "executed"
        row["text"] = text
        self._audit(row, "approved_once", "executed", "pc-gateway")
        self._write_last(row)
        return row

    def request(self, kind: str, target: str, *, mode: str = "ask_each",
                actor: str = "owner") -> dict:
        if mode not in _MODES:
            raise ValueError("invalid_mode")
        target = str(target or "").strip()
        if kind == "run_command":
            red = _red_line(target)
            if red:
                row = {
                    "id": "act-" + uuid.uuid4().hex[:10], "kind": kind,
                    "target": target, "status": "refused", "reason": "red_line:" + red,
                    "text": "هذا الأمر ممنوع permanently (خط أحمر): " + red,
                }
                self._audit(row, None, "refused", actor)
                self._write_last(row)
                return row
        elif kind == "open_url":
            if not is_public_web_url(target):
                row = {
                    "id": "act-" + uuid.uuid4().hex[:10], "kind": kind,
                    "target": target, "status": "refused", "reason": "unsafe_url",
                    "text": "الرابط غير مسموح (محلي/خاص أو scheme غير HTTP).",
                }
                self._audit(row, None, "refused", actor)
                self._write_last(row)
                return row
        else:
            row = {"id": "act-" + uuid.uuid4().hex[:10], "kind": kind,
                   "target": target, "status": "refused", "reason": "unknown_kind",
                   "text": "نوع الفعل غير معروف."}
            self._audit(row, None, "refused", actor)
            self._write_last(row)
            return row

        row = {
            "id": "act-" + uuid.uuid4().hex[:10], "kind": kind, "target": target,
            "status": "proposed", "reason": None, "text": "", "mode": mode,
        }
        self._plans[row["id"]] = row
        self._audit(row, None, "proposed", actor)

        if mode == "auto":
            self._audit(row, "proposed", "approved_once", actor)
            return self._execute(row)
        key = (kind, target)
        if mode == "session" and key in self._session_grants:
            self._audit(row, "proposed", "approved_once", "session-grant")
            return self._execute(row)
        return dict(row)

    def decide(self, action_id: str, decision: str, *, actor: str = "hud") -> dict:
        if decision not in _DECISIONS:
            raise ValueError("invalid_decision")
        row = self._plans.get(str(action_id))
        if row is None or row.get("status") != "proposed":
            raise ValueError("invalid_transition")
        previous = "proposed"
        row["status"] = decision
        self._audit(row, previous, decision, actor)
        if decision == "denied":
            row["text"] = "رفضت الفعل؛ ما وقع أي تنفيذ."
            self._write_last(row)
            return dict(row)
        if row.get("mode") == "session":
            self._session_grants.add((row["kind"], row["target"]))
        return self._execute(row)


def gateway() -> PcGateway:
    """مثيل محلي واحد، يُستعمل من Atulya وواجهة HUD."""
    global _GATEWAY
    if _GATEWAY is None:
        _GATEWAY = PcGateway()
    return _GATEWAY


_GATEWAY: PcGateway | None = None
