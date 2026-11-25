#!/usr/bin/env python3
"""
J62 — ESPRIEAETHER VOICE DAEMON — 24/7, 100 % local.

ميكروفون دايم → Whisper محلي → دماغ :31416 → SAPI (سبيكرات PC).
كل دورة كتكتب فـ state/voice_inbox.jsonl باش الوكيل يقرأ الكلام وينفّذو.
لا كاين أي سيرفيس سحابي، لا كاين أي مفتاح، والفشل كيتسجّل بصدق.

التشغيل:
  python voice_daemon.py              # دايم
  python voice_daemon.py --once       # دورة واحدة (اختبار)
  python voice_daemon.py --seconds 3  # مدة الاستماع
"""

import difflib
import json
import logging
import os
import re
import signal
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "src"))

import action_request  # noqa: E402
import local_voice  # noqa: E402
import run_store  # noqa: E402
import voice_inbox  # noqa: E402
import voice_loop  # noqa: E402
import voice_status  # noqa: E402
from singleton import SingletonLock  # noqa: E402

LOG_FILE = BASE_DIR / "voice_daemon.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("voice-daemon")

SECONDS = float(os.getenv("SUNNAVOK_VOICE_SECONDS", "5"))
INTERVAL = float(os.getenv("SUNNAVOK_VOICE_DAEMON_INTERVAL", "1"))
# darija (arabe marocain) : l'auto-détection Whisper gère l'arabe, le français
# et le mixte des deux ; un réglage explicite reste possible via l'environnement.
_LANG = (os.getenv("SUNNAVOK_VOICE_LANGUAGE") or "auto").strip().lower()
LANGUAGE = None if _LANG in ("auto", "auto-detect", "") else ("ar" if _LANG in ("ar", "darija", "arabe", "marocain") else _LANG)
ECHO_WINDOW = float(os.getenv("SUNNAVOK_VOICE_ECHO_WINDOW", "20"))
BARGE_THRESHOLD = float(os.getenv("SUNNAVOK_BARGE_THRESHOLD", "0.18"))
_last_spoken = {"text": "", "ts": 0.0}
_mic_state = {"level": 0.0}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(text or "").lower())).strip()


def _is_echo(text: str) -> bool:
    """يتجنب الجواب على صوت السبيكرات اللي سمعو الميكروفون."""
    previous = str(_last_spoken.get("text") or "")
    if not previous or time.monotonic() - float(_last_spoken.get("ts") or 0) > ECHO_WINDOW:
        return False
    a, b = _normalize(text), _normalize(previous)
    if not a or not b:
        return False
    return a == b or (len(a) >= 12 and (a in b or b in a)) or \
        difflib.SequenceMatcher(None, a, b).ratio() >= 0.85


def _listen_filtered(seconds: float, language=None) -> dict:
    result = local_voice.listen(seconds=seconds, language=language)
    if result.get("ok") and _is_echo(str(result.get("text") or "")):
        return {"ok": False, "text": "", "language": result.get("language"),
                "reason": "echo_suppressed"}
    return result


def _mic_level() -> float:
    """Niveau RMS local calculé par le moniteur ; aucun réseau, aucun modèle."""
    try:
        return float(_mic_state.get("level") or 0.0)
    except (TypeError, ValueError):
        return 0.0


class MicEnergyMonitor:
    """Surveille l'énergie micro locale pendant la lecture et permet un reset propre."""

    def __init__(self, threshold: float = BARGE_THRESHOLD) -> None:
        self.threshold = float(threshold)
        self.suppress_until = 0.0
        self._stream = None

    def start(self) -> bool:
        try:
            import numpy as np  # sounddevice l'exige déjà ; aucun réseau ici
            import sounddevice as sd  # dépendance locale déjà utilisée par le STT

            def callback(indata, frames, time_info, status):
                # sounddevice fournit un tableau (frames, canaux) : jamais de
                # `indata or []` ici, car la valeur booléenne d'un tableau est
                # ambiguë et faisait échouer le callback en silence.
                values = np.asarray(indata, dtype=np.float32).ravel()
                _mic_state["level"] = (
                    float(np.sqrt(np.mean(values * values))) if values.size else 0.0
                )

            self._stream = sd.InputStream(channels=1, callback=callback)
            self._stream.start()
            return True
        except Exception:
            self._stream = None
            return False

    def suppress(self, seconds: float) -> None:
        """Le système ne doit jamais se réveiller avec sa propre voix."""
        self.suppress_until = time.monotonic() + max(0.0, float(seconds))

    def reset(self) -> None:
        self.suppress_until = 0.0
        _mic_state["level"] = 0.0

    def triggered(self) -> bool:
        if time.monotonic() < self.suppress_until:
            return False
        try:
            return _mic_level() >= self.threshold
        except Exception:
            return False

    def stop(self) -> None:
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
        self.reset()


def _record_brain_metrics(metrics: dict) -> None:
    """Mesure réelle du cerveau local : aucun texte ni secret n'est écrit."""
    voice_loop.write_brain_metrics(metrics)


def _inbox() -> voice_inbox.VoiceInbox:
    return voice_inbox.VoiceInbox()


def _set_stage(stage: str, level: float = 0.0, reason=None) -> dict:
    """État vocal public pour le visage ; aucun texte, aucun secret."""
    return voice_status.write(stage, level, reason)


def probe() -> dict:
    """حالة صادقة للمايكروفون والسبيكرات والدماغ وصندوق النص."""
    chain = voice_loop.probe()
    voice = local_voice.probe()
    available = bool(chain.get("available") and voice.get("stt") and voice.get("tts"))
    return {
        "available": available,
        "mode": "always_on_voice" if available else "no_local_voice_loop",
        "mic": bool(voice.get("stt")),
        "speakers": bool(voice.get("tts")),
        "brain": chain.get("brain"),
        "inbox": str(voice_inbox.INBOX_PATH),
        "status": voice_status.read(),
        "reason": None if available else (chain.get("reason") or "voice_unavailable"),
    }


def once(seconds: float = SECONDS, language=LANGUAGE, barge_monitor=None) -> dict:
    """دورة واحدة: استماع → دماغ محلي → نطق → كتابة فالصندوق، مع مقاطعة محلية."""
    _set_stage("listening", 0.35)
    cancel_fn = barge_monitor.triggered if barge_monitor is not None else None
    result = voice_loop.voice_turn(seconds=seconds, language=language,
                                   listen_fn=_listen_filtered,
                                   status_fn=_set_stage,
                                   metrics_fn=_record_brain_metrics,
                                   cancel_fn=cancel_fn,
                                   action_store=action_request.default_store())
    if result.get("reason") == "barge_in":
        if barge_monitor is not None:
            barge_monitor.reset()
        _last_spoken["text"] = ""
        _last_spoken["ts"] = 0.0
        _set_stage("idle", 0.0, "barge_in")
    elif result.get("ok") and result.get("spoken"):
        _last_spoken["text"] = str(result.get("reply") or "")
        _last_spoken["ts"] = time.monotonic()
        if barge_monitor is not None:
            barge_monitor.suppress(max(2.0, len(_last_spoken["text"]) / 12.0))
        _set_stage("idle")
    elif not result.get("ok"):
        _set_stage("idle", 0.0, str(result.get("reason") or "turn_failed"))
    _inbox().append(result)
    return result


def main() -> None:
    lock_dir = BASE_DIR / "state"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock = SingletonLock("voice_daemon", lock_dir)
    if not lock.acquire():
        logger.info("another instance is already running — exiting")
        return

    try:
        if "--seconds" in sys.argv:
            try:
                global SECONDS
                SECONDS = float(sys.argv[sys.argv.index("--seconds") + 1])
            except (IndexError, ValueError):
                pass

        stop = {"flag": False}

        def handler(sig, frame):
            logger.info("shutdown signal received")
            stop["flag"] = True

        signal.signal(signal.SIGINT, handler)
        signal.signal(signal.SIGTERM, handler)

        logger.info("=" * 60)
        logger.info(f"VOICE DAEMON — mic={probe()['mic']} speakers={probe()['speakers']}")
        logger.info(f"listen={SECONDS}s interval={INTERVAL}s inbox={voice_inbox.INBOX_PATH}")
        logger.info("=" * 60)

        monitor = MicEnergyMonitor()
        logger.info("local mic barge-in monitor: %s", "on" if monitor.start() else "unavailable")
        while not stop["flag"]:
            try:
                result = once(barge_monitor=monitor)
                if not result.get("ok"):
                    logger.warning("turn failed: %s", result.get("reason"))
            except Exception as exc:  # لا نوقف الدايم بسبب دورة فاشلة
                logger.error("turn error: %s", type(exc).__name__)
            for _ in range(max(1, int(INTERVAL * 2))):
                if stop["flag"]:
                    break
                time.sleep(0.5)

        logger.info("voice daemon stopped")
    finally:
        try:
            monitor.stop()
        except Exception:
            pass
        lock.release()


if __name__ == "__main__":
    if "--once" in sys.argv:
        payload = once()
        shown = dict(payload)
        for key in ("heard", "reply"):
            if isinstance(shown.get(key), str):
                shown[key] = run_store.redact(shown[key])
        print(json.dumps(shown, ensure_ascii=False))
        sys.exit(0 if payload.get("ok") else 1)
    main()
