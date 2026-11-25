"""Politique d'URL partagée : ports valides, pas d'identifiants ni de requête."""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1"})


@dataclass(frozen=True, slots=True)
class URLPolicy:
    """Règles communes aux points d'accès MCP, à la page d'accueil et à l'origine publique."""

    label: str
    message: str
    scheme: str = "https"                 # "https", "loopback_http" ou "any"
    loopback_hosts_only: bool = False
    allow_localhost: bool = False
    require_port: bool = False
    require_root_path: bool = False

    def parse(self, url: str) -> SplitResult:
        """Valide et renvoie l'URL découpée ; aucun accès réseau, aucun secret."""
        stripped = url.strip() if isinstance(url, str) else ""
        if not stripped or stripped.endswith(("?", "#")):
            raise ValueError(self.message)
        parts = urlsplit(stripped)
        # Un port explicitement vide (`http://127.0.0.1:/`) vaut None pour urlsplit.
        if parts.netloc.endswith(":"):
            raise ValueError(self.message)
        try:
            port = parts.port
        except ValueError as exc:
            raise ValueError(f"{self.label} contains an invalid port") from exc
        host = parts.hostname
        loopback = host in LOOPBACK_HOSTS
        if self.scheme == "https":
            scheme_ok = parts.scheme == "https"
        elif self.scheme == "loopback_http":
            scheme_ok = parts.scheme == "https" or (parts.scheme == "http" and loopback)
        else:
            scheme_ok = parts.scheme in {"http", "https"}
        if self.loopback_hosts_only:
            host_ok = loopback
        elif self.allow_localhost:
            host_ok = bool(host) and (parts.scheme != "http" or loopback or host == "localhost")
        else:
            host_ok = bool(host)
        if (
            not scheme_ok
            or not host_ok
            or (port is not None and not 1 <= port <= 65535)
            or (self.require_port and port is None)
            or parts.username is not None
            or parts.password is not None
            or parts.query
            or parts.fragment
            or (self.require_root_path and parts.path not in {"", "/"})
        ):
            raise ValueError(self.message)
        return parts


MCP_POLICY = URLPolicy(
    label="MCP endpoint",
    message="Use an HTTPS MCP endpoint, or a loopback HTTP MCP endpoint "
            "(127.0.0.1 or ::1), without credentials or query parameters",
    scheme="loopback_http",
)
LANDING_POLICY = URLPolicy(
    label="ATULYA_LANDING_URL",
    message="ATULYA_LANDING_URL must be a loopback HTTP(S) URL without credentials or query parameters",
    scheme="loopback_http",
    loopback_hosts_only=True,
    require_port=True,
)
PUBLIC_ORIGIN_POLICY = URLPolicy(
    label="ATULYA_PUBLIC_ORIGIN",
    message="ATULYA_PUBLIC_ORIGIN must be an HTTPS origin (HTTP is allowed only for localhost)",
    scheme="any",
    allow_localhost=True,
    require_root_path=True,
)
