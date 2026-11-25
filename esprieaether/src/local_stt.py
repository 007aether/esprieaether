"""J57 — reconnaissance vocale RÉELLEMENT locale (Whisper / faster-whisper).

Le modèle et l'audio ne quittent jamais la machine : aucun appel réseau au
moment de transcrire. Le téléchargement initial du modèle public (sans clé)
est le seul usage Internet, autorisé explicitement par l'utilisateur en J57.

Aucun secret n'est lu, stocké ou journalisé ici.
"""

from __future__ import annotations

import os
import tempfile
import wave
from pathlib import Path
from typing import Dict, Optional

BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BASE_DIR.parent
MODEL_DIR = PROJECT_ROOT / "models" / "stt"
MODEL_NAME = os.environ.get("SUNNAVOK_STT_MODEL", "base")
SAMPLE_RATE = 16000
ENGINE = "faster-whisper"

_MODEL = None


def _engine_available() -> bool:
    try:
        import faster_whisper  # noqa: F401

        return True
    except Exception:
        return False


def _model_cached() -> bool:
    """Vrai si le modèle est déjà sur disque → aucun accès réseau au chargement."""
    return bool(MODEL_DIR.is_dir()) and any(
        MODEL_DIR.rglob("model.bin")
    )


def _get_model():
    """Charge le modèle local une seule fois.

    Si le modèle est déjà sur disque, ``local_files_only=True`` garantit
    zéro requête réseau (même au démarrage à froid). Le tout premier
    téléchargement public, sans clé, reste possible sinon.
    """
    global _MODEL
    if _MODEL is None:
        from faster_whisper import WhisperModel

        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        _MODEL = WhisperModel(
            MODEL_NAME,
            device="cpu",
            compute_type="int8",
            download_root=str(MODEL_DIR),
            local_files_only=_model_cached(),
        )
    return _MODEL


def probe() -> Dict[str, object]:
    """Capacités publiques — statut honnête, jamais de succès simulé."""
    if not _engine_available():
        return {
            "available": False, "mode": "no_local_stt", "engine": None,
            "model": MODEL_NAME, "reason": "engine_not_installed",
        }
    try:
        _get_model()
    except Exception as exc:
        return {
            "available": False, "mode": "no_local_stt", "engine": ENGINE,
            "model": MODEL_NAME, "reason": f"model_unavailable:{type(exc).__name__}",
        }
    return {
        "available": True, "mode": "local_whisper", "engine": ENGINE,
        "model": MODEL_NAME, "reason": None,
    }


def transcribe_file(path, language: Optional[str] = None) -> Dict[str, object]:
    """Transcrit un fichier audio local. Aucun octet n'est envoyé hors machine."""
    target = Path(str(path)) if path else None
    if target is None or not target.is_file():
        return {"ok": False, "text": "", "language": None, "engine": ENGINE,
                "reason": "file_not_found"}
    if not _engine_available():
        return {"ok": False, "text": "", "language": None, "engine": ENGINE,
                "reason": "engine_not_installed"}
    try:
        segments, info = _get_model().transcribe(
            str(target), language=language, vad_filter=True
        )
        text = " ".join(
            segment.text.strip()
            for segment in segments
            if getattr(segment, "text", None) and segment.text.strip()
        )
        lang = getattr(info, "language", None) or language
        return {"ok": True, "text": text, "language": lang, "engine": ENGINE,
                "reason": None}
    except Exception as exc:
        return {"ok": False, "text": "", "language": None, "engine": ENGINE,
                "reason": str(exc)[:200]}


def _record_wav(path, seconds: float) -> None:
    """Capture micro locale (PortAudio) → WAV 16 kHz mono, stdlib wave."""
    import sounddevice as sd

    frames = int(max(0.5, float(seconds)) * SAMPLE_RATE)
    audio = sd.rec(frames, samplerate=SAMPLE_RATE, channels=1, dtype="int16")
    sd.wait()
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(audio.tobytes())


def record_and_transcribe(seconds: float = 5, language: Optional[str] = None) -> Dict[str, object]:
    """Écoute locale puis transcription locale. Rien ne sort du poste."""
    if not _engine_available():
        return {"ok": False, "text": "", "language": None, "engine": ENGINE,
                "reason": "no_local_stt", "audioSeconds": 0}
    try:
        duration = max(0.5, float(seconds))
    except (TypeError, ValueError):
        duration = 5.0
    with tempfile.TemporaryDirectory(prefix="sunnavok-stt-") as tmp:
        wav = Path(tmp) / "utterance.wav"
        try:
            _record_wav(wav, duration)
        except Exception as exc:
            return {"ok": False, "text": "", "language": None, "engine": ENGINE,
                    "reason": f"mic_unavailable:{type(exc).__name__}",
                    "audioSeconds": 0}
        result = transcribe_file(wav, language=language)
    result["audioSeconds"] = duration
    return result


__all__ = [
    "MODEL_DIR", "MODEL_NAME", "ENGINE", "probe", "transcribe_file",
    "record_and_transcribe",
]
