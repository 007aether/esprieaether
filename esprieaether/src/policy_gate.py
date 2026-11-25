"""Politique d'autorité locale du JARVIS SUNNAVOK (J52).

L'utilisateur a accordé l'autorité locale complète. Le gate ne retire aucun
pouvoir à l'agent à l'intérieur du périmètre du projet ; il empêche seulement
de toucher aux secrets et de sortir sur le réseau externe — deux lignes rouges
fixées par l'utilisateur lui-même et maintenues intactes.

Aucun secret n'est lu, stocké ou journalisé ici.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import re
from typing import Dict, Optional

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class AuthorityMode(str, Enum):
    FULL_LOCAL = "full_local"
    FULL_INTERNET = "full_internet"
    READ_ONLY = "read_only"


# Actions que le JARVIS local peut exécuter. Tout le reste est refusé, même en
# autorité complète : l'autorité n'est pas une absence de périmètre.
ALLOWLIST = frozenset({
    "inspect", "read", "list", "get", "status", "health", "check", "verify",
    "scan", "analyze", "decompile", "research", "audit", "monitor", "plan",
    "decide", "delegate", "dashboard", "speak", "listen", "brain_reply",
    "voice_turn", "learn", "test",
    "write", "edit", "create", "delete", "remove", "restart", "start", "stop",
    "run", "execute", "run_robot", "connect", "backup", "repair", "heal", "build",
})

EFFECTFUL = frozenset({
    "write", "edit", "create", "delete", "remove", "restart", "start",
    "stop", "run", "execute", "connect", "backup", "repair", "build",
})

READ_ONLY_ALLOWED = frozenset({
    "inspect", "read", "list", "get", "status", "health", "check", "verify",
    "scan", "analyze", "decompile", "research", "audit", "monitor", "plan",
    "decide", "dashboard", "learn", "test",
})

# Les rôles réels des robots sont ajoutés à l'allowlist s'ils sont importables.
try:
    import sys

    sys.path.insert(0, str(PROJECT_ROOT / "robots"))
    import robot_engine  # type: ignore

    ALLOWLIST = ALLOWLIST | frozenset(getattr(robot_engine, "ROLE_HANDLERS", {}).keys())
except Exception:  # pragma: no cover - dépend de l'environnement d'exécution
    pass

# Noms de fichiers / dossiers protégés. La règle porte sur le nom, pas sur le
# contenu : aucun fichier protégé n'est ouvert pour décider.
_PROTECTED_EXACT = frozenset({
    ".env", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519", "vault.key",
    ".credentials.yaml", "credentials.json", "secrets.json",
})
_PROTECTED_SUFFIX = (".pem", ".key", ".pfx", ".p12")
_PROTECTED_DIRS = (".ssh", ".claude", "node_modules")

_LOOPBACK = re.compile(r"^(?:127\.0\.0\.1|localhost|\[::1\]|::1)(?::\d+)?$", re.I)
_PRIVATE_LITERAL = re.compile(
    r"^(?:10\.|127\.|169\.254\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.)", re.I
)
_IPV4 = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")


@dataclass(frozen=True)
class Decision:
    action: str
    allowed: bool
    mode: str
    reason: str
    tainted: bool = False
    requires_confirmation: bool = False

    def to_dict(self) -> Dict[str, object]:
        # asdict ne contient que des champs publics : aucune donnée secrète.
        return asdict(self)


def _name_and_parts(path: str) -> tuple[str, tuple[str, ...]]:
    normalized = str(path).replace("/", "\\")
    parts = tuple(p.lower() for p in normalized.split("\\") if p)
    return (parts[-1] if parts else ""), parts


def protected_path(path: str) -> bool:
    name, parts = _name_and_parts(path)
    lower = name.lower()
    if lower.startswith(".env"):
        return True
    if lower in _PROTECTED_EXACT:
        return True
    if lower.endswith(_PROTECTED_SUFFIX):
        return True
    return any(p in _PROTECTED_DIRS for p in parts[:-1])


def loopback_host(host: str) -> bool:
    return bool(_LOOPBACK.match(str(host).strip()))


def host_kind(host: str) -> str:
    """loopback | private | public — bloque aussi les noms qui déguisent une IP privée."""
    value = str(host).strip().lower()
    if loopback_host(value):
        return "loopback"
    bare = value.split(":", 1)[0].strip("[]")
    if _PRIVATE_LITERAL.match(bare) or bare.startswith("localhost."):
        return "private"
    return "public"


def decide(
    action: str,
    *,
    path: Optional[str] = None,
    host: Optional[str] = None,
    mode: AuthorityMode = AuthorityMode.FULL_LOCAL,
    tainted: bool = False,
    source: Optional[str] = None,
    internet: bool = True,
) -> Decision:
    """Rend une décision publique et traçable. Ne touche à aucune ressource.

    L'utilisateur a accordé l'accès Internet (J57) : les hôtes publics sont
    autorisés, les réseaux privés restent bloqués (SSRF) et les secrets/chemins
    protégés restent intouchables.
    """
    action = str(action).strip().lower()
    mode_value = mode.value if isinstance(mode, AuthorityMode) else str(mode)
    if mode_value == AuthorityMode.FULL_INTERNET.value:
        internet = True
    if mode_value == AuthorityMode.READ_ONLY.value:
        internet = False

    if path is not None and protected_path(path):
        return Decision(action, False, mode_value, "protected_path", tainted)

    if host is not None:
        kind = host_kind(host)
        if kind == "private":
            return Decision(action, False, mode_value, "private_network", tainted)
        if kind == "public" and not internet:
            return Decision(action, False, mode_value, "external_network", tainted)

    if action not in ALLOWLIST:
        return Decision(action, False, mode_value, "not_allowlisted", tainted)

    if mode_value == AuthorityMode.READ_ONLY.value and action not in READ_ONLY_ALLOWED:
        return Decision(action, False, mode_value, "read_only_mode", tainted)

    confirmation = bool(tainted and action in EFFECTFUL)
    reason = "internet_allowed" if (host is not None and host_kind(host) == "public") else "allowlisted"
    return Decision(action, True, mode_value, reason, tainted, confirmation)


def check_url(
    url: str,
    *,
    action: str = "connect",
    mode: AuthorityMode = AuthorityMode.FULL_LOCAL,
    internet: bool = True,
) -> Decision:
    """Décision d'egress pour une URL : scheme autorisé + hôte vérifié.

    Ne contacte jamais l'hôte. Les URL privées/LAN sont refusées même avec
    l'autorité Internet, et les schemes non HTTP(S) sont refusés.
    """
    from urllib.parse import urlparse

    value = str(url or "").strip()
    try:
        parsed = urlparse(value)
        scheme = (parsed.scheme or "").lower()
        host = parsed.hostname or ""
        port = parsed.port
    except ValueError:
        return Decision(str(action), False, mode.value, "invalid_url")
    if scheme not in ("http", "https"):
        return Decision(str(action), False, mode.value, "unsupported_scheme")
    if not host:
        return Decision(str(action), False, mode.value, "missing_host")
    target = host if port is None else f"{host}:{port}"
    return decide(str(action), host=target, mode=mode, internet=internet)


__all__ = [
    "AuthorityMode", "Decision", "ALLOWLIST", "EFFECTFUL", "PROJECT_ROOT",
    "check_url", "decide", "host_kind", "loopback_host", "protected_path",
]
