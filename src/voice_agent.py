#!/usr/bin/env python3
"""
voice_agent.py — voice in / voice out for the Telegram bot + API

WHAT: Turns Telegram voice notes and API audio into text (STT) and text into
voice (TTS), so the user can talk to the system from the phone instead of
typing — and hear answers back.

WHY: hands-free control of a 24/7 agent stack. The user is often away from a
keyboard; voice is the natural channel. Also used by the autonomous loop to
speak Telegram alerts.

STT chain (first that works wins):
  1. Groq Whisper API (whisper-large-v3-turbo) — needs GROQ_API_KEY, fast
  2. LLM7 whisper-large-v3 — keyless fallback
TTS chain:
  1. edge-tts (free Microsoft voices, pip) — Arabic/Darija-friendly voices
  2. gTTS (Google Translate TTS, free, needs network)
  3. silent failure (text only)

Input formats: Telegram voice = .ogg opus; uploads = .wav/.mp3/.m4a/.ogg.
Whisper APIs accept all of these directly.
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env", override=True)
except ImportError:
    pass

GROQ_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
LLM7_KEY = os.getenv("LLM7_API_KEY", "none")
LLM7_STT_URL = "https://api.llm7.io/v1/audio/transcriptions"

logger = logging.getLogger("voice_agent")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")


# ── STT ──

def _multipart_transcribe(url, api_key, model, file_path, lang=None):
    """POST an audio file as multipart to an OpenAI-compatible STT endpoint."""
    boundary = "----aethervoice" + os.urandom(8).hex()
    filename = os.path.basename(file_path)
    mime = {
        ".ogg": "audio/ogg", ".oga": "audio/ogg", ".opus": "audio/ogg",
        ".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4",
        ".webm": "audio/webm", ".flac": "audio/flac",
    }.get(Path(filename).suffix.lower(), "application/octet-stream")

    with open(file_path, "rb") as f:
        audio_bytes = f.read()

    parts = []
    for name, value in (("model", model), ("response_format", "json")):
        if value:
            parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode()
            )
    if lang:
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{language}\"\r\n\r\n{lang}\r\n".encode()
        )
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
        f"Content-Type: {mime}\r\n\r\n".encode() + audio_bytes + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
        return (data.get("text") or "").strip()
    except urllib.error.HTTPError as e:
        logger.warning(f"  STT HTTP {e.code} from {url}")
        return ""
    except Exception as e:
        logger.warning(f"  STT error from {url}: {e}")
        return ""


def transcribe(file_path, lang=None):
    """Transcribe audio → text. Returns (text, engine)."""
    if not Path(file_path).exists():
        return "", "none"

    # 1. Groq (fast, needs key)
    if GROQ_KEY:
        text = _multipart_transcribe(GROQ_STT_URL, GROQ_KEY, "whisper-large-v3-turbo", file_path, lang)
        if text:
            return text, "groq"

    # 2. LLM7 (keyless)
    text = _multipart_transcribe(LLM7_STT_URL, LLM7_KEY, "whisper-large-v3", file_path, lang)
    if text:
        return text, "llm7"

    return "", "none"


# ── TTS ──

def _pip_available(module):
    try:
        __import__(module)
        return True
    except ImportError:
        return False


def synthesize(text, out_path, voice="ar-EG-SalmaNeural", rate="+0%"):
    """Text → speech file (.mp3/.ogg). Returns (path, engine) or ('', engine)."""
    # 1. edge-tts (best Arabic voices, free)
    if _pip_available("edge_tts"):
        try:
            import asyncio
            import edge_tts

            async def _run():
                communicate = edge_tts.Communicate(text, voice, rate=rate)
                await communicate.save(out_path)

            asyncio.run(_run())
            if Path(out_path).exists() and Path(out_path).stat().st_size > 100:
                return out_path, "edge-tts"
        except Exception as e:
            logger.warning(f"  edge-tts failed: {e}")

    # 2. gTTS
    if _pip_available("gtts"):
        try:
            from gtts import gTTS
            gTTS(text=text, lang="ar" if voice.startswith("ar") else "en").save(out_path)
            if Path(out_path).exists() and Path(out_path).stat().st_size > 100:
                return out_path, "gtts"
        except Exception as e:
            logger.warning(f"  gtts failed: {e}")

    return "", "none"


def speak_telegram(text, voice="ar-EG-SalmaNeural"):
    """Synthesize for Telegram — returns a file path ready to send, or ''."""
    out = Path(tempfile.gettempdir()) / f"aether_voice_{os.urandom(4).hex()}.mp3"
    path, engine = synthesize(text, str(out), voice=voice)
    if path:
        logger.info(f"  TTS [{engine}] → {path}")
        return path
    logger.warning("  TTS: no engine available (install edge-tts)")
    return ""


def format_telegram():
    """Voice subsystem status for /voice."""
    groq = "✅" if GROQ_KEY else "❌"
    edge = "✅" if _pip_available("edge_tts") else "❌ (pip install edge-tts)"
    gtts = "✅" if _pip_available("gtts") else "❌"
    return (
        "🎙️ *Voice Agent*\n\n"
        f"STT Groq (whisper-turbo): {groq}\n"
        f"STT LLM7 (whisper-v3): ✅ (keyless)\n"
        f"TTS edge-tts (أصوات عربية): {edge}\n"
        f"TTS gTTS: {gtts}\n\n"
        "صيف voice فـ Telegram → كيترجم لك\n"
        "أو /voice say <text> → كيقرا لك"
    )


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcribe", help="audio file path")
    ap.add_argument("--lang", default=None, help="language hint (ar, fr, en)")
    ap.add_argument("--say", help="text to speak")
    ap.add_argument("--voice", default="ar-EG-SalmaNeural")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    if args.status:
        print(format_telegram())
    elif args.transcribe:
        text, engine = transcribe(args.transcribe, lang=args.lang)
        print(f"[{engine}] {text}")
    elif args.say:
        path = speak_telegram(args.say, voice=args.voice)
        print(f"[tts] {path or 'FAILED'}")
    else:
        print(format_telegram())


if __name__ == "__main__":
    main()
