#!/usr/bin/env python3
"""J159 — voix locale d'Atulya pour le HUD, sans cloud ni clé.

Le moteur Supertonic déjà présent dans l'import Atulya-Tantra est réutilisé
tel quel : il tourne en local sur CPU, produit un WAV, et rien ne quitte la
machine. Ce service n'envoie aucun SMS, n'appelle aucun appareil et ne touche
jamais au lanceur USB propriétaire.
"""

from __future__ import annotations

import hashlib
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BASE_DIR.parent
ATULYA_DIR = ROOT_DIR / "GITHUB_IMPORT" / "Atulya-Tantra"
if str(ATULYA_DIR) not in sys.path:
    sys.path.insert(0, str(ATULYA_DIR))

from tools.plugins.voice.providers import VoiceError  # noqa: E402
from tools.plugins.voice.tts import LocalSupertonicTTS  # noqa: E402

HOST = "127.0.0.1"
PORT = 5105
CACHE_DIR = BASE_DIR / "state" / "voice_say_cache"
MAX_CHARS = 500
MAX_BODY = 4096

_engine: Optional[LocalSupertonicTTS] = None
_lock = threading.Lock()


def engine() -> LocalSupertonicTTS:
    global _engine
    if _engine is None:
        with _lock:
            if _engine is None:
                _engine = LocalSupertonicTTS(ATULYA_DIR / "models")
    return _engine


def ready() -> bool:
    try:
        return engine().ready
    except Exception:
        return False


def synthesize(text: str, language: str = "auto") -> bytes:
    """Texte → WAV local, mis en cache par empreinte du texte et de la langue."""
    clean = str(text or "").strip()
    if not clean:
        raise VoiceError("Texte vide : rien à prononcer.")
    if len(clean) > MAX_CHARS:
        raise VoiceError(f"Texte trop long ({len(clean)}/{MAX_CHARS}).")
    lang = str(language or "auto").strip() or "auto"
    key = hashlib.sha256(f"{lang}\n{clean}".encode("utf-8")).hexdigest()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached = CACHE_DIR / f"{key}.wav"
    if cached.is_file():
        return cached.read_bytes()
    audio = engine().synthesize(clean, language=lang)
    if not audio.startswith(b"RIFF"):
        raise VoiceError("Le moteur local n'a pas produit de WAV valide.")
    tmp = cached.with_name(f".{cached.name}.{hashlib.sha1(audio).hexdigest()[:8]}.tmp")
    tmp.write_bytes(audio)
    tmp.replace(cached)
    return audio


class Handler(BaseHTTPRequestHandler):
    server_version = "ESPRIEATHER-LocalVoice/1.0"

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _wav(self, audio: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(audio)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(audio)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.split("?", 1)[0] != "/health":
            self._json(404, {"ok": False, "reason": "not_found"})
            return
        up = ready()
        self._json(200, {
            "ok": up,
            "status": "live_verified" if up else "needs_user_data",
            "engine": "supertonic-3-int8-local",
            "readOnly": True,
            "reason": None if up else "modele vocal local absent",
        })

    def do_POST(self) -> None:  # noqa: N802
        if self.path.split("?", 1)[0] != "/say":
            self._json(404, {"ok": False, "reason": "not_found"})
            return
        try:
            size = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            size = 0
        if size <= 0 or size > MAX_BODY:
            self._json(400, {"ok": False, "reason": "corps invalide"})
            return
        try:
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
            text = payload.get("text") if isinstance(payload, dict) else None
            language = payload.get("language", "auto") if isinstance(payload, dict) else "auto"
            self._wav(synthesize(str(text or ""), str(language)))
        except VoiceError as exc:
            self._json(400, {"ok": False, "reason": str(exc)[:160]})
        except Exception as exc:
            self._json(503, {"ok": False, "reason": type(exc).__name__})

    def log_message(self, fmt: str, *args) -> None:
        return  # aucun texte parlé n'est journalisé


def main() -> int:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
