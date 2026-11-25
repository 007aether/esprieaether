"""J58 — chaîne vocale 100 % locale : micro → Whisper → cerveau :31416 → SAPI.

Aucun texte parlé ne quitte la machine. Le cerveau local est le seul endpoint
contacté, en loopback, sans clé ni en-tête d'autorisation. Chaque étape passe
par ``policy_gate.decide()`` et se termine dans le journal ``RunStore`` avec
un état terminal. Aucun secret n'est lu, journalisé ou renvoyé.
"""

from __future__ import annotations

import json
import os
import re
import socket
import time
import urllib.error
import urllib.request
from typing import Dict, Optional

import local_voice
import policy_gate
import run_store
from policy_gate import decide

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRAIN_HOST = "127.0.0.1:31416"
BRAIN_URL = "http://127.0.0.1:31416/v1/chat/completions"
MODEL = os.getenv("SUNNAVOK_VOICE_MODEL", "dolphin3")
TIMEOUT = float(os.getenv("SUNNAVOK_VOICE_TIMEOUT", "45"))
MAX_REPLY_CHARS = 500
MAX_SPOKEN_CHARS = 220
METRICS_PATH = os.path.join(BASE_DIR, "state", "brain_metrics.json")

# Les hôtes sont vérifiés par le gate avant toute connexion. Aucune valeur
# sensible (clé, token) n'est stockée ici : le cerveau local n'en exige pas.

# Le 3B local ne comprend pas la darija écrite en latin et renvoie la question
# telle quelle. On la ramène en lettres arabes avant de l'envoyer au cerveau.
_DARIJA_PHRASES = (
    ("salamu alaykum", "السلام عليكم"),
    ("salam, kifach ndir", "السلام عليكم، كي داير؟"),
    ("salam kifach ndir", "السلام عليكم، كي داير؟"),
    ("kifach ndir", "كي داير؟"),
    ("ki dayer", "كي داير؟"),
    ("chno lhal", "شنو الحال؟"),
)
_DARIJA_WORDS = {
    "salam": "السلام عليكم",
    "wach": "واش",
    "bghiti": "بغيتي",
    "bghit": "بغيت",
    "chokran": "شكرا",
    "labas": "لا باس",
    "kayn": "كاين",
}


def _has_arabic(value: str) -> bool:
    return any("\u0600" <= char <= "\u06ff" for char in value)


def normalize_darija(text: str) -> str:
    """Convertit la darija latine connue en lettres arabes, sans réseau."""
    value = str(text or "").strip()
    if not value or _has_arabic(value):
        return value
    for phrase, arabic in _DARIJA_PHRASES:
        value = re.sub(re.escape(phrase), arabic, value, flags=re.IGNORECASE)
    for word, arabic in _DARIJA_WORDS.items():
        value = re.sub(rf"\b{re.escape(word)}\b", arabic, value, flags=re.IGNORECASE)
    if _has_arabic(value):
        value = value.replace(",", "،").replace("?", "؟")
        value = re.sub(r"؟+", "؟", value)
        value = re.sub(r"،+", "،", value)
    return value


def _store() -> run_store.RunStore:
    return run_store.RunStore(os.path.join(BASE_DIR, "state", "run_ledger.db"))


def probe() -> Dict[str, object]:
    """Capacités publiques de la chaîne, sans contact réseau."""
    voice = local_voice.probe()
    gate = decide("voice_turn", host=BRAIN_HOST)
    available = bool(voice.get("available") and gate.allowed)
    return {
        "available": available,
        "mode": "local_voice_loop" if available else "no_local_voice_loop",
        "tts": bool(voice.get("tts")),
        "stt": bool(voice.get("stt")),
        "brain": BRAIN_HOST if gate.allowed else None,
        "reason": None if available else "voice_or_gate_unavailable",
    }


def _fail(store: run_store.RunStore, run_id: int, reason: str) -> Dict[str, object]:
    store.update(run_id, "failed", f"reason={reason}")
    return {
        "ok": False, "heard": "", "reply": "", "spoken": False,
        "language": None, "engine": None, "reason": reason,
    }


def write_brain_metrics(metrics: Dict[str, object], path: str = METRICS_PATH) -> bool:
    """Écrit une mesure locale bornée ; aucun texte parlé ni secret n'est conservé."""
    try:
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        payload = {
            "available": bool(metrics.get("available")),
            "model": str(metrics.get("model") or MODEL)[:80],
            "promptTokens": metrics.get("promptTokens"),
            "completionTokens": metrics.get("completionTokens"),
            "elapsedMs": metrics.get("elapsedMs"),
            "tokensPerSecond": metrics.get("tokensPerSecond"),
            "checkedAt": metrics.get("checkedAt"),
            "reason": metrics.get("reason"),
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)
        return True
    except (OSError, TypeError, ValueError):
        return False


def brain_reply(
    text: str,
    model: str = MODEL,
    timeout: float = TIMEOUT,
    metrics_fn=None,
) -> Dict[str, object]:
    """Envoie le texte au cerveau local uniquement, sans secret ni fallback."""
    store = _store()
    run_id = store.record("brain_reply", actor="local_brain", detail=f"model={model}")
    gate = decide("connect", host=BRAIN_HOST)
    if not gate.allowed:
        return _fail(store, run_id, f"gate_denied:{gate.reason}")
    message = normalize_darija(str(text).strip())
    if not message:
        return _fail(store, run_id, "empty_input")
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": (
                "Réponds en arabe marocain avec lettres arabes. Une seule phrase courte. "
                "N'écris aucune lettre latine dans la réponse. "
                "Comprends la darija écrite en latin (kifach, ki dayer, wach, bghiti). "
                "Ne promets aucune action : propose-la seulement, une approbation explicite est requise."
            )},
            {"role": "user", "content": message},
        ],
        "temperature": 0.3,
        "max_tokens": 120,
    }
    request = urllib.request.Request(
        BRAIN_URL,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
        elapsed_ms = int(max(0.0, time.monotonic() - started) * 1000)
        data = json.loads(raw)
        content = data["choices"][0]["message"]["content"]
        reply = str(content).strip()[:MAX_REPLY_CHARS]
    except urllib.error.HTTPError as exc:
        return _fail(store, run_id, f"brain_http_{exc.code}")
    except (socket.timeout, TimeoutError):
        return _fail(store, run_id, "brain_timeout")
    except urllib.error.URLError as exc:
        return _fail(store, run_id, f"brain_unreachable:{type(exc.reason).__name__}")
    except (KeyError, IndexError, TypeError, ValueError):
        return _fail(store, run_id, "brain_bad_response")
    if not reply:
        return _fail(store, run_id, "brain_empty")
    usage = data.get("usage") or {}
    completion = usage.get("completion_tokens")
    prompt = usage.get("prompt_tokens")
    completion = int(completion) if isinstance(completion, (int, float)) and completion >= 0 else None
    prompt = int(prompt) if isinstance(prompt, (int, float)) and prompt >= 0 else None
    rate = None
    reason = None
    if completion is None or elapsed_ms <= 0:
        reason = "no_usage_data"
    else:
        rate = round(completion / (elapsed_ms / 1000.0), 2)
    metrics = {
        "available": rate is not None,
        "model": model,
        "promptTokens": prompt,
        "completionTokens": completion,
        "elapsedMs": elapsed_ms,
        "tokensPerSecond": rate,
        "checkedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "reason": reason,
    }
    if callable(metrics_fn):
        try:
            metrics_fn(metrics)
        except Exception:
            pass
    store.update(run_id, "succeeded", f"model={model} chars={len(reply)}")
    return {
        "ok": True, "text": reply, "model": model,
        "engine": "local-brain", "reason": None,
        "elapsedMs": elapsed_ms, "tokensPerSecond": rate,
    }


def _spoken_text(reply: str) -> str:
    """Raccourcit la prononciation sans toucher à la réponse renvoyée."""
    text = str(reply or "").strip()
    if len(text) <= MAX_SPOKEN_CHARS:
        return text
    cut = text[:MAX_SPOKEN_CHARS]
    boundary = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return (cut[:boundary + 1] if boundary > MAX_SPOKEN_CHARS // 2 else cut).strip()


def _emit(status_fn, stage: str, level: float = 0.0, reason: str = None) -> None:
    """Notifie l'interface sans jamais lui donner de texte brut."""
    if callable(status_fn):
        try:
            status_fn(stage, round(max(0.0, min(1.0, float(level))), 2), reason)
        except Exception:
            pass


def _cancelled(cancel_fn) -> bool:
    """Interruption locale uniquement : jamais une commande ni un risseau externe."""
    if not callable(cancel_fn):
        return False
    try:
        return bool(cancel_fn())
    except Exception:
        return False


def voice_turn(
    seconds: float = 5,
    language: Optional[str] = None,
    speak_reply: bool = True,
    model: str = MODEL,
    listen_fn=None,
    status_fn=None,
    metrics_fn=None,
    cancel_fn=None,
    action_store=None,
) -> Dict[str, object]:
    """Une tournée complète : écoute, réponse locale, prononciation locale."""
    store = _store()
    run_id = store.record("voice_turn", actor="voice_loop", detail=f"listen={seconds}s")
    gate = decide("voice_turn", host=BRAIN_HOST)
    if not gate.allowed:
        reason = f"gate_denied:{gate.reason}"
        _emit(status_fn, "idle", 0.0, reason)
        return _fail(store, run_id, reason)

    _emit(status_fn, "listening", 0.35)
    listener = listen_fn if callable(listen_fn) else local_voice.listen
    heard = listener(seconds=seconds, language=language)
    if not heard.get("ok"):
        reason = f"listen:{heard.get('reason') or 'no_local_stt'}"
        _emit(status_fn, "idle", 0.0, reason)
        return _fail(store, run_id, reason)
    text = str(heard.get("text") or "").strip()
    if not text:
        _emit(status_fn, "idle", 0.0, "empty_transcript")
        return _fail(store, run_id, "empty_transcript")

    if _cancelled(cancel_fn):
        _emit(status_fn, "idle", 0.0, "barge_in")
        return _fail(store, run_id, "barge_in")

    _emit(status_fn, "thinking", 0.6)
    brain = brain_reply(text, model=model, metrics_fn=metrics_fn)
    if not brain.get("ok"):
        reason = str(brain.get("reason") or "brain_failed")
        _emit(status_fn, "idle", 0.0, reason)
        return _fail(store, run_id, reason)

    approval = None
    raw_action = brain.get("action")
    if isinstance(raw_action, dict) and action_store is not None:
        try:
            approval = action_store.propose(
                str(raw_action.get("action") or "run"),
                target=str(raw_action.get("target") or ""),
                reason=str(raw_action.get("reason") or ""),
                source="voice",
            )
        except (OSError, TypeError, ValueError):
            approval = None

    spoken = False
    if _cancelled(cancel_fn):
        _emit(status_fn, "idle", 0.0, "barge_in")
        return _fail(store, run_id, "barge_in")
    if speak_reply:
        gate_speak = decide("speak")
        if not gate_speak.allowed:
            reason = f"gate_denied:{gate_speak.reason}"
            _emit(status_fn, "idle", 0.0, reason)
            return _fail(store, run_id, reason)
        reply = str(brain.get("text") or "")
        if approval is not None:
            reply = "Action proposée, en attente d'approbation explicite."
        _emit(status_fn, "speaking", 0.5 + min(len(reply), 500) / 1000.0)
        result = local_voice.speak(_spoken_text(reply), stop_fn=cancel_fn)
        if not result.get("ok"):
            why = str(result.get("reason") or "sapi_failed")
            reason = "barge_in" if why == "barge_in" else f"speak:{why}"
            _emit(status_fn, "idle", 0.0, reason)
            return _fail(store, run_id, reason)
        spoken = True

    store.update(run_id, "succeeded",
                 f"heard={len(text)} reply={len(str(brain.get('text') or ''))}")
    _emit(status_fn, "idle")
    return {
        "ok": True,
        "heard": text,
        "reply": str(brain.get("text") or ""),
        "spoken": spoken,
        "language": heard.get("language"),
        "engine": brain.get("engine"),
        "model": brain.get("model"),
        "approval": approval,
        "approvalPending": approval is not None and approval.get("status") == "proposed",
        "reason": None,
    }


__all__ = [
    "BRAIN_HOST", "BRAIN_URL", "MODEL", "METRICS_PATH", "probe", "brain_reply",
    "voice_turn", "write_brain_metrics",
]
