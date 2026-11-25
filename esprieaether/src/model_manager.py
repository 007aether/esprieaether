"""Téléchargement local résilient des modèles GGUF.

Reprise HTTP Range, petits blocs, nouvelles tentatives, vérification SHA-256
et remplacement atomique. Aucun dépendance externe, aucun appel cloud.
Extrait du motif utilisé par xark-argo/argo (gestionnaire de modèles local).
"""
from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen

USER_AGENT = "ESPRIEATHER/2.0 (local-model-manager)"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resilient_download(url: str, target: Path, expected_sha256: str,
                       chunk_size: int = 64 * 1024, timeout: float = 45.0,
                       max_attempts: int = 250) -> Path:
    """Télécharge `url` vers `target`, en reprenant depuis le fichier .part."""
    target = Path(target)
    part = target.with_suffix(target.suffix + ".part")
    if target.is_file() and (not expected_sha256 or sha256_file(target) == expected_sha256):
        return target

    total = 0
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        start = part.stat().st_size if part.is_file() else 0
        if total and start >= total:
            break
        headers = {"User-Agent": USER_AGENT}
        if start:
            headers["Range"] = f"bytes={start}-"
        try:
            request = Request(url, headers=headers)
            with urlopen(request, timeout=timeout) as response:
                if start and response.status != 206:
                    raise OSError(f"Range ignoré par le serveur: {response.status}")
                match = re.search(r"/([0-9]+)$", response.headers.get("Content-Range", ""))
                if match:
                    total = int(match.group(1))
                with part.open("ab" if start else "wb") as output:
                    while chunk := response.read(chunk_size):
                        output.write(chunk)
                        start += len(chunk)
            print(f"ATTEMPT={attempt} BYTES={start} TOTAL={total}", flush=True)
            last_error = None
            break
        except Exception as exc:  # coupure réseau, timeout, TLS, etc.
            last_error = exc
            now = part.stat().st_size if part.is_file() else 0
            print(f"RETRY={attempt} OFFSET={now} ERROR={type(exc).__name__}: {str(exc)[:100]}",
                  flush=True)
            time.sleep(0)

    if last_error is not None:
        raise last_error
    final = part.stat().st_size if part.is_file() else 0
    if total and final != total:
        raise OSError(f"Téléchargement incomplet: {final}/{total}")
    digest = sha256_file(part)
    if expected_sha256 and digest != expected_sha256:
        raise ValueError(f"SHA-256 inattendu: {digest}")
    part.replace(target)
    return target
