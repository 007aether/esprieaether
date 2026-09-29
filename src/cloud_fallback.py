# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

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

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
TOGETHER_BASE_URL = os.getenv("TOGETHER_BASE_URL", "https://api.together.xyz/v1")
TOGETHER_MODEL = os.getenv("TOGETHER_MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "openbmb/MiniCPM5-2B")
OLLAMA_MODEL_FAST = os.getenv("OLLAMA_MODEL_FAST", "qwen2.5:3b")
OLLAMA_MODEL_BALANCED = os.getenv("OLLAMA_MODEL_BALANCED", "openbmb/MiniCPM5-2B")
OLLAMA_MODEL_DEEP = os.getenv("OLLAMA_MODEL_DEEP", "hf.co/OrionLLM/GRM2-3b-GGUF:Q4_K_M")

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
            socket.create_connection(("1.1.1.1", 53), timeout=5)
            self.online = True
        except Exception:
            self.online = False
        self.last_check = now
        return self.online

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
                    "X-Title": "EsprieAether",
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": messages,
                    "temperature": 0.5,
                    "max_tokens": 4000,
                },
                timeout=30,
            )
            if r.status_code == 200:
                return {"status": "ok", "provider": "openrouter",
                        "answer": r.json()["choices"][0]["message"]["content"]}
            return {"status": "skip", "reason": "HTTP " + str(r.status_code)}
        except Exception as e:
            return {"status": "skip", "reason": str(e)[:100]}

    def _try_groq(self, messages: list) -> dict:
        if not GROQ_API_KEY:
            return {"status": "skip", "reason": "no key"}
        try:
            r = requests.post(
                GROQ_BASE_URL + "/chat/completions",
                headers={
                    "Authorization": "Bearer " + GROQ_API_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": messages,
                    "temperature": 0.5,
                    "max_tokens": 4000,
                },
                timeout=30,
            )
            if r.status_code == 200:
                return {"status": "ok", "provider": "groq",
                        "answer": r.json()["choices"][0]["message"]["content"]}
            return {"status": "skip", "reason": "HTTP " + str(r.status_code)}
        except Exception as e:
            return {"status": "skip", "reason": str(e)[:100]}

    def _try_together(self, messages: list) -> dict:
        if not TOGETHER_API_KEY:
            return {"status": "skip", "reason": "no key"}
        try:
            r = requests.post(
                TOGETHER_BASE_URL + "/chat/completions",
                headers={
                    "Authorization": "Bearer " + TOGETHER_API_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "model": TOGETHER_MODEL,
                    "messages": messages,
                    "temperature": 0.5,
                    "max_tokens": 4000,
                },
                timeout=30,
            )
            if r.status_code == 200:
                return {"status": "ok", "provider": "together",
                        "answer": r.json()["choices"][0]["message"]["content"]}
            return {"status": "skip", "reason": "HTTP " + str(r.status_code)}
        except Exception as e:
            return {"status": "skip", "reason": str(e)[:100]}

    def _pick_model(self, prompt: str) -> str:
        """اختيار النموذج حسب نوع المهمة"""
        p = prompt.lower()
        
        # مهام الكود والتعديل → Balanced
        code_keywords = ["def ", "class ", "return ", "import ", "python", 
                         "code", "كود", "دالة", "ملف", "تعديل", "suggest"]
        if any(kw in p for kw in code_keywords):
            return OLLAMA_MODEL_BALANCED
        
        # مهام التحليل المعقد → Deep
        deep_keywords = ["analyze", "explain", "why", "compare", "تحليل", "اشرح", "قارن"]
        if any(kw in p for kw in deep_keywords):
            return OLLAMA_MODEL_DEEP
        
        # الباقي → Fast
        return OLLAMA_MODEL_FAST
    
    def _try_gemini(self, messages: list) -> dict:
        if not GEMINI_API_KEY:
            return {"status": "skip", "reason": "no key"}
        try:
            from google import genai

            client = genai.Client(api_key=GEMINI_API_KEY)

            # ابنِ النص
            text_parts = []
            for m in messages:
                text_parts.append(m.get("content", ""))
            prompt = chr(10).join(text_parts)

            # جرّب النماذج المتاحة
            models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
            last_error = ""

            for model_name in models:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )
                    answer = response.text if response.text else ""
                    if answer:
                        return {"status": "ok", "provider": "gemini", "answer": answer}
                except Exception as e:
                    last_error = str(e)[:150]
                    continue

            return {"status": "skip", "reason": last_error}
        except ImportError:
            return {"status": "skip", "reason": "google-genai not installed"}
        except Exception as e:
            return {"status": "skip", "reason": str(e)[:150]}


    def _try_local(self, messages: list) -> dict:
        try:
            # اختر النموذج حسب آخر رسالة
            last_msg = messages[-1].get("content", "") if messages else ""
            model = self._pick_model(last_msg)
            
            r = requests.post(
                OLLAMA_HOST + "/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.5, "num_ctx": 65536},
                },
                timeout=300,
            )
            r.raise_for_status()
            return {"status": "ok", "provider": "local",
                    "answer": r.json()["message"]["content"]}
        except Exception as e:
            return {"status": "error", "reason": str(e)[:100]}

    def ask(self, prompt: str, system: str = None, prefer: str = "auto") -> dict:
        """إرسال مع Multi-Provider Fallback"""
        # Local فقط
        if prefer == "local":
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            result = self._try_local(messages)
            if result["status"] == "ok":
                self._record("local", "ok")
            else:
                self._record("local", "error")
            return result

        # Cloud فقط
        if prefer == "cloud":
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            for func, name in [
                (self._try_openrouter, "openrouter"),
                (self._try_groq, "groq"),
                (self._try_together, "together"),
            ]:
                result = func(messages)
                if result["status"] == "ok":
                    self._record(name, "ok")
                    logger.info("☁️ " + name)
                    return {"status": "ok", "source": name, "answer": result["answer"]}
                self._record(name, "skip")

            logger.warning("⚠️ كل المزودين فشلوا — Local")
            result = self._try_local(messages)
            if result["status"] == "ok":
                self._record("local", "ok")
                return {"status": "ok", "source": "local", "answer": result["answer"]}
            return {"status": "error", "message": "كل المزودين فشلوا"}

        # auto
        if not self.is_online():
            return self.ask(prompt, system, "local")
        return self.ask(prompt, system, "cloud")

    def _record(self, provider: str, status: str):
        if provider not in self.state["requests"]:
            self.state["requests"][provider] = 0
            self.state["failures"][provider] = 0
        if status == "ok":
            self.state["requests"][provider] += 1
        else:
            self.state["failures"][provider] += 1
        self.state["last_switch"] = datetime.now().isoformat()
        self._save_state()

    def get_cost_report(self) -> dict:
        """تقرير استخدام المزودين"""
        report = {
            "total_requests": 0,
            "total_failures": 0,
            "success_rate": 0,
            "by_provider": {},
        }

        for provider, count in self.state.get("requests", {}).items():
            fails = self.state.get("failures", {}).get(provider, 0)
            total = count + fails
            rate = round((count / total * 100), 1) if total > 0 else 0
            report["by_provider"][provider] = {
                "success": count,
                "failures": fails,
                "success_rate": rate,
            }
            report["total_requests"] += count
            report["total_failures"] += fails

        total = report["total_requests"] + report["total_failures"]
        if total > 0:
            report["success_rate"] = round(report["total_requests"] / total * 100, 1)

        return report

    def format_cost_report(self) -> str:
        """تنسيق للتلغرام"""
        r = self.get_cost_report()

        text = "💰 *Cost Report*" + chr(10) + chr(10)
        text += "📊 إجمالي: `" + str(r["total_requests"]) + "` نجاح" + chr(10)
        text += "❌ فشل: `" + str(r["total_failures"]) + "`" + chr(10)
        text += "✅ معدل النجاح: `" + str(r["success_rate"]) + "%`" + chr(10)
        text += chr(10)

        if r["by_provider"]:
            text += "*حسب المزود:*" + chr(10)
            for p, data in r["by_provider"].items():
                text += "• `" + p + "`: " + str(data["success"]) + " نجاح, " + str(data["failures"]) + " فشل (" + str(data["success_rate"]) + "%)" + chr(10)

        return text

    def status(self) -> dict:
        return {
            "online": self.is_online(force=True),
            "providers": {
                "openrouter": bool(OPENROUTER_API_KEY),
                "groq": bool(GROQ_API_KEY),
                "together": bool(TOGETHER_API_KEY),
                "gemini": bool(GEMINI_API_KEY),
                "local": True,
            },
            "requests": self.state.get("requests", {}),
            "failures": self.state.get("failures", {}),
            "last_switch": self.state.get("last_switch"),
        }

    def format_telegram(self) -> str:
        s = self.status()
        emoji = "🟢" if s["online"] else "🔴"

        text = "☁️ *Cloud Fallback v2*" + chr(10) + chr(10)
        text += emoji + " الإنترنت: `" + ("متصل" if s["online"] else "منقطع") + "`" + chr(10) + chr(10)

        text += "*المزودون:*" + chr(10)
        for name, available in s["providers"].items():
            e = "✅" if available else "❌"
            reqs = s["requests"].get(name, 0)
            fails = s["failures"].get(name, 0)
            text += e + " `" + name + "`: " + str(reqs) + " نجاح, " + str(fails) + " فشل" + chr(10)

        text += chr(10) + "_آخر تبديل: `" + str(s["last_switch"] or "—")[:19] + "`_"
        return text


if __name__ == "__main__":
    print("═" * 60)
    print("☁️ Cloud Fallback v2 Test")
    print("═" * 60)

    c = CloudFallback()
    print(c.format_telegram())
    print()

    r = c.ask("قل: مرحبا", prefer="cloud")
    print("▶ Cloud:", r.get("source"), "-", (r.get("answer") or "")[:50])

    r = c.ask("قل: مرحبا", prefer="local")
    print("▶ Local:", r.get("source"), "-", (r.get("answer") or "")[:50])
