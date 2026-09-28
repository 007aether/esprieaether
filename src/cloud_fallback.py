"""
⚡ EsprieAether - Cloud Fallback
طبقة التبديل التلقائي: Cloud (DeepSeek) ↔ Local (Ollama)
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

# ─── الإعدادات ───
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free")

# نماذج احتياطية (تجربتها بالترتيب) - الأسرع أولاً
OPENROUTER_MODELS_FALLBACK = [
    "cohere/north-mini-code:free",           # 2s
    "dots-studio/dots-3-note-preview:free",  # 2s
    "nvidia/nemotron-3.5-lightning:free",    # بطيء لكن قوي
]

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-64k")

CHECK_INTERVAL = 30  # ثانية
STATE_FILE = BASE_DIR / "cloud_fallback_state.json"


class CloudFallback:
    """مدير التبديل بين Cloud و Local"""

    def __init__(self):
        self.last_check = 0
        self.online = None  # None = لم يُفحص بعد
        self.state = self._load_state()

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except Exception:
                pass
        return {
            "started_at": datetime.now().isoformat(),
            "cloud_requests": 0,
            "local_requests": 0,
            "cloud_failures": 0,
            "last_switch": None,
        }

    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2, ensure_ascii=False))

    # ─────────────────────────────────────
    #  فحص الإنترنت
    # ─────────────────────────────────────
    def is_online(self, force: bool = False) -> bool:
        """فحص الاتصال بالإنترنت (مع cache 30 ثانية)"""
        now = time.time()
        if not force and self.online is not None and (now - self.last_check) < CHECK_INTERVAL:
            return self.online

        # افحص DeepSeek أولاً
        try:
            r = requests.head(DEEPSEEK_BASE_URL, timeout=5)
            self.online = r.status_code < 500
        except Exception:
            # افحص الإنترنت العام
            try:
                socket.create_connection(("1.1.1.1", 53), timeout=5)
                self.online = True
            except Exception:
                self.online = False

        self.last_check = now
        return self.online

    # ─────────────────────────────────────
    #  إرسال الطلبات
    # ─────────────────────────────────────
    def ask(self, prompt: str, system: str = None, prefer: str = "auto") -> dict:
        """
        إرسال طلب مع تبديل تلقائي
        
        prefer: "auto" | "cloud" | "local"
        """
        online = self.is_online()

        # القرار
        if prefer == "local" or (prefer == "auto" and not online):
            return self._ask_local(prompt, system)
        else:
            result = self._ask_cloud(prompt, system)
            if result["status"] == "ok":
                return result

            # فشل Cloud → Local
            logger.warning("⚠️ Cloud فشل — التبديل إلى Local")
            self.state["cloud_failures"] += 1
            self._save_state()
            return self._ask_local(prompt, system)

    def _ask_cloud(self, prompt: str, system: str = None) -> dict:
        """إرسال إلى Cloud (OpenRouter أولاً، ثم Groq)"""

        # 1. OpenRouter
        if OPENROUTER_API_KEY:
            try:
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})

                r = requests.post(
                    OPENROUTER_BASE_URL + "/chat/completions",
                    headers={
                        "Authorization": "Bearer " + OPENROUTER_API_KEY,
                        "Content-Type": "application/json",
                        "HTTP-Referer": "http://localhost:5000",
                        "X-Title": "EsprieAether",
                    },
                    json={
                        "model": OPENROUTER_MODEL,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 4000,
                    },
                    timeout=30,
                )

                if r.status_code == 200:
                    data = r.json()
                    answer = data["choices"][0]["message"]["content"]
                    self.state["cloud_requests"] += 1
                    self.state["last_switch"] = datetime.now().isoformat()
                    self._save_state()
                    logger.info("☁️ OpenRouter")
                    return {"status": "ok", "source": "cloud", "answer": answer}
                elif r.status_code == 429:
                    logger.warning("⚠️ OpenRouter 429 — جاري Groq")
                else:
                    logger.warning("⚠️ OpenRouter " + str(r.status_code))
            except Exception as e:
                logger.error("OpenRouter: " + str(e))

        # 2. Groq
        if GROQ_API_KEY:
            try:
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})

                r = requests.post(
                    GROQ_BASE_URL + "/chat/completions",
                    headers={
                        "Authorization": "Bearer " + GROQ_API_KEY,
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": GROQ_MODEL,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 4000,
                    },
                    timeout=30,
                )

                if r.status_code == 200:
                    data = r.json()
                    answer = data["choices"][0]["message"]["content"]
                    self.state["cloud_requests"] += 1
                    self.state["last_switch"] = datetime.now().isoformat()
                    self._save_state()
                    logger.info("⚡ Groq")
                    return {"status": "ok", "source": "cloud", "answer": answer}
                else:
                    logger.error("Groq " + str(r.status_code) + ": " + r.text[:200])
            except Exception as e:
                logger.error("Groq: " + str(e))

        return {"status": "error", "message": "كل المزودين فشلوا"}


    def _ask_local(self, prompt: str, system: str = None) -> dict:
        """إرسال إلى Ollama المحلي"""
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            r = requests.post(
                f"{OLLAMA_HOST}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.5, "num_ctx": 65536},
                },
                timeout=300,
            )
            r.raise_for_status()
            data = r.json()
            answer = data["message"]["content"]

            self.state["local_requests"] += 1
            self.state["last_switch"] = datetime.now().isoformat()
            self._save_state()

            logger.info("🏠 Local (Ollama)")
            return {"status": "ok", "source": "local", "answer": answer}

        except Exception as e:
            logger.error(f"❌ Local: {e}")
            return {"status": "error", "message": str(e)}

    # ─────────────────────────────────────
    #  التقرير
    # ─────────────────────────────────────
    def status(self) -> dict:
        """حالة النظام"""
        return {
            "online": self.is_online(force=True),
            "cloud_available": bool(OPENROUTER_API_KEY),
            "cloud_model": OPENROUTER_MODEL,
            "local_model": OLLAMA_MODEL,
            "requests": {
                "cloud": self.state["cloud_requests"],
                "local": self.state["local_requests"],
                "cloud_failures": self.state["cloud_failures"],
            },
            "last_switch": self.state["last_switch"],
        }

    def format_telegram(self) -> str:
        """تنسيق للـ Telegram"""
        s = self.status()
        emoji_online = "🟢" if s["online"] else "🔴"
        emoji_cloud = "✅" if s["cloud_available"] else "❌"

        return f"""
☁️ *Cloud Fallback*

{emoji_online} الإنترنت: `{'متصل' if s['online'] else 'منقطع'}`
{emoji_cloud} Cloud: `{'جاهز' if s['cloud_available'] else 'غير مُعدّ'}`

*النماذج:*
• Cloud: `{s['cloud_model']}`
• Local: `{s['local_model']}`

*الإحصائيات:*
• Cloud requests: `{s['requests']['cloud']}`
• Local requests: `{s['requests']['local']}`
• Cloud failures: `{s['requests']['cloud_failures']}`

_آخر تبديل: `{s['last_switch'] or '—'}`_
"""


# ─── اختبار ───
if __name__ == "__main__":
    print("═" * 60)
    print("☁️ Cloud Fallback Test")
    print("═" * 60)

    fb = CloudFallback()
    print(f"\n▶ الحالة:\n{fb.format_telegram()}")

    if OPENROUTER_API_KEY:
        print("\n▶ اختبار Cloud...")
        result = fb.ask("قل: مرحبا", prefer="cloud")
        print(f"  {result}")
    else:
        print("\n⚠️ DEEPSEEK_API_KEY غير موجود — اختبار Local فقط")
        result = fb.ask("قل: مرحبا", prefer="local")
        print(f"  {result}")
