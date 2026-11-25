"""Singleton local basé sur un fichier-verrou (stdlib uniquement).

Empêche deux instances du même daemon de tourner en parallèle. Le fichier ne
contient qu'un PID : aucun secret, aucune donnée d'exécution. Un PID mort est
considéré comme un verrou périmé et peut être repris.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":  # pragma: no cover - dépend de la plateforme
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            # ERROR_ACCESS_DENIED (5) : le processus existe mais appartient à
            # une intégrité supérieure. Le considérer comme mort permettrait
            # à une seconde instance de voler le verrou.
            return ctypes.get_last_error() == 5
        kernel32.CloseHandle(handle)
        return True
    try:  # pragma: no cover - dépend de la plateforme
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


class SingletonLock:
    def __init__(self, name: str, directory):
        self.path = Path(directory) / f"{str(name).strip()}.lock"
        self.acquired = False

    def acquire(self) -> bool:
        if self.path.exists():
            try:
                pid = int(self.path.read_text(encoding="ascii").strip())
            except (OSError, ValueError):
                pid = 0
            if _pid_alive(pid):
                return False
            try:
                self.path.unlink()
            except OSError:
                return False
        try:
            fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        try:
            os.write(fd, str(os.getpid()).encode("ascii"))
        finally:
            os.close(fd)
        self.acquired = True
        return True

    def release(self) -> None:
        if self.acquired:
            try:
                self.path.unlink(missing_ok=True)
            finally:
                self.acquired = False


__all__ = ["SingletonLock"]
