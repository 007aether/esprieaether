"""J55 — voix 100 % locale, sans clé ni service cloud.

Si aucun moteur n'est présent, le module le dit explicitement au lieu de
simuler une réussite. Aucun texte parlé n'est envoyé hors de la machine.
"""

from __future__ import annotations

import re
import subprocess
from typing import Callable, Dict, Optional, Tuple

import local_stt

MAX_CHUNK_CHARS = 180
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _run_powershell(command: str, timeout: int = 15) -> Tuple[bool, str]:
    """Exécute une commande PowerShell locale, sans élévation ni réseau."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode == 0, (result.stdout or result.stderr or "").strip()
    except Exception as exc:  # pragma: no cover - dépend de l'environnement
        return False, type(exc).__name__


def _sapi_available() -> bool:
    ok, _ = _run_powershell(
        "Add-Type -AssemblyName System.Speech; "
        "[bool]([System.Speech.Synthesis.SpeechSynthesizer] -ne $null)"
    )
    return ok


def _stt_available() -> bool:
    """Vrai STT local : Whisper embarqué, pas un stub."""
    return bool(local_stt.probe().get("available"))


def probe() -> Dict[str, object]:
    """Capacités publiques : aucun nom de champ ne contient de donnée sensible."""
    tts = _sapi_available()
    stt = _stt_available()
    available = bool(tts or stt)
    return {
        "available": available,
        "mode": "offline" if available else "no_local_voice",
        "tts": bool(tts),
        "stt": bool(stt),
        "engine": "sapi_tts" if tts else None,
        "reason": None if available else "no_local_voice",
    }


def split_ready(text: str) -> list[str]:
    """Découpe en phrases courtes, sans vide, pour préparer la suite pendant la lecture."""
    normalized = re.sub(r"\s+", " ", str(text or "")).strip()
    if not normalized:
        return []
    chunks: list[str] = []
    for part in (piece.strip() for piece in _SENTENCE_END.split(normalized)):
        while len(part) > MAX_CHUNK_CHARS:
            cut = part[:MAX_CHUNK_CHARS]
            split_at = cut.rfind(" ")
            if split_at < MAX_CHUNK_CHARS // 2:
                split_at = MAX_CHUNK_CHARS
            chunks.append(cut[:split_at].strip())
            part = part[split_at:].strip()
        if part:
            chunks.append(part)
    return chunks


def speak(text: str, stop_fn: Optional[Callable[[], bool]] = None) -> Dict[str, object]:
    """Prononce localement via SAPI, phrase par phrase, avec arrêt possible entre deux."""
    if not _sapi_available():
        return {"ok": False, "engine": None, "reason": "no_local_voice"}
    chunks = split_ready(text)
    if not chunks:
        return {"ok": False, "engine": None, "reason": "empty_text", "chunks": 0}
    spoken = 0
    for chunk in chunks:
        safe = chunk.replace("'", "''")
        command = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Speak('{safe}'); $s.Dispose()"
        )
        ok, output = _run_powershell(command, timeout=45)
        if not ok:
            return {
                "ok": False, "engine": None, "chunks": spoken + 1,
                "reason": (output[:160] or "sapi_failed"),
            }
        spoken += 1
        if callable(stop_fn) and stop_fn():
            return {
                "ok": False, "engine": "sapi_tts", "chunks": spoken,
                "reason": "barge_in", "stopped": True,
            }
    return {"ok": True, "engine": "sapi_tts", "chunks": spoken, "reason": None}


def listen(seconds: float = 5, language: Optional[str] = None) -> Dict[str, object]:
    """Micro local → Whisper local. Aucune clé, aucun service cloud."""
    result = local_stt.record_and_transcribe(seconds=seconds, language=language)
    if not result.get("ok"):
        return {"ok": False, "text": "",
                "reason": result.get("reason") or "no_local_stt"}
    return {
        "ok": True,
        "text": result.get("text", ""),
        "language": result.get("language"),
        "engine": result.get("engine"),
        "audioSeconds": result.get("audioSeconds"),
        "reason": None,
    }


__all__ = ["probe", "speak", "listen", "split_ready"]
