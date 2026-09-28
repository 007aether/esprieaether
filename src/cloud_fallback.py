"""
⚡ EsprieAether - Cloud Fallback v2
Multi-Provider: OpenRouter → Groq → Together → Local
"""
import os
import time
import json
import socket
import logging
import requests
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path.home() / "AETHER_V8"
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("cloud_fallback")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

# ─── Providers ───
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "dots-studio/dots-3-note-preview:free")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY", "")
TOGETHER_BASE_URL = os.getenv("TOGETHER_BASE_URL", "https://api.together.xyz/v1")
TOGETHER_MODEL = os.getenv("TOGETHER_MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-64k")

CHECK_INTERVAL = 30
STATE_FILE = BASE_DIR / "cloud_fallback_state.json"


class CloudFallback:
    """Multi-Provider Fallback"""

    def __init__(self):
        self.last_check = 0
        self.online = None
        self.state = self._load_state()

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except Exception:
                pass
        return {
            "started_at": datetime.now().isoformat(),
            "requests": {},
            "failures": {},
            "last_switch": None,
        }

    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2, ensure_ascii=False))

    def is_online(self, force: bool = False) -> bool:
        now = time.time()
        if not force and self.online is not None and (now - self.last_check) < CHECK_INTERVAL:
            return self.online
        try:
            socket.create_connection(("1.1.1.1", 53), timeout=3)
            self.online = True
        except Exception:
            self.online = False
        self.last_check = now
        return self.online

    # ─────────────────────────────────────
    #  المحاولات
    # ─────────────────────────────────────
    def _try_openrouter(self, messages: list) -> dict:
        if not OPENROUTER_API_KEY:
            return {"status": "skip", "reason": "no key"}
        try:
            r = requests.post(
                OPENROUTER_BASE_URL + "/chat/completions",
                headers={
                    "Authorization": "Bearer " + OPENROUTER_API_KEY,
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://localhost:5000",
                    "X-Title": "EsprieAether"
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": messages
                },
                timeout=60
            )
            r.raise_for_status()
            data = r.json()
            return {
                "status": "success",
                "provider": "openrouter",
                "response": data["choices"][0]["message"]["content"]
            }
        except Exception as e:
            return {"status": "error", "provider": "openrouter", "reason": str(e)}