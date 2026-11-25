"""Garde de sortie locale : loopback pour les modèles, HTTPS public pour les liens.

Inspiré des histoires Hacker News #3 (modèles qui parlent à des serveurs
externes), #8 (prise de contrôle de sous-domaines), #18 (coût cloud imprévu) et
#21 (campagne d'intrusion). Aucun appel réseau ici : cette couche ne fait que
décider ce qui est autorisé avant qu'une requête ou un bouton soit créé.
"""
from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

LOCAL_SUFFIXES = (".localhost", ".local", ".internal")
LOCAL_NAMES = {"localhost", "localhost.localdomain"}


def _host_is_local(host: str) -> bool:
    name = host.strip().rstrip(".").lower()
    if not name or name in LOCAL_NAMES or name.endswith(LOCAL_SUFFIXES):
        return True
    try:
        address = ipaddress.ip_address(name)
    except ValueError:
        return False
    return (address.is_loopback or address.is_private or address.is_link_local
            or address.is_multicast or address.is_reserved or address.is_unspecified)


def _parts(url: str):
    try:
        return urlsplit(url)
    except ValueError:
        return None


def is_loopback_url(url: str) -> bool:
    """Vrai seulement pour une adresse locale explicite, sans identifiants."""
    parts = _parts(url)
    if parts is None or parts.scheme not in ("http", "https") or not parts.hostname:
        return False
    if parts.username or parts.password:
        return False
    host = parts.hostname.rstrip(".").lower()
    if host in LOCAL_NAMES or host.endswith(LOCAL_SUFFIXES):
        return host in LOCAL_NAMES
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def assert_loopback_url(url: str, *, allowed_schemes=("http",)) -> str:
    """Refuse tout modèle ou service qui ne tourne pas sur la boucle locale."""
    parts = _parts(url)
    if parts is None or parts.scheme not in allowed_schemes:
        raise ValueError(f"schéma non autorisé pour une adresse locale: {url!r}")
    if not parts.hostname or parts.username or parts.password:
        raise ValueError(f"adresse locale invalide: {url!r}")
    if not is_loopback_url(url):
        raise ValueError(f"seule la boucle locale est autorisée: {url!r}")
    return url.rstrip("/")


def is_public_https_url(url: str) -> bool:
    """Vrai pour un lien HTTPS public, faux pour tout réseau interne/privé."""
    parts = _parts(url)
    if parts is None or parts.scheme != "https" or not parts.hostname:
        return False
    if parts.username or parts.password or parts.query or parts.fragment:
        return False
    return not _host_is_local(parts.hostname)
