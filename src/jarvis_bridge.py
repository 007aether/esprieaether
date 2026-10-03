# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

"""
⚡ EsprieAether - Jarvis Bridge
جسر الاتصال مع الذكاء المحلي (Ollama / Qwen / Hermes)
"""
import os
import json
import logging
from pathlib import Path
from typing import Optional, Generator

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

logger = logging.getLogger("jarvis_bridge")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


class JarvisBridge:
    """جسر موحّد للتواصل مع الذكاء المحلي"""

    def __init__(self, host: str = OLLAMA_HOST, model: str = OLLAMA_MODEL):
        self.host = host.rstrip("/")
        self.model = model
        self.history: list = []
        self.max_history = 20

    def ping(self) -> dict:
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=5)
            r.raise_for_status()
            models = [m["name"] for m in r.json().get("models", [])]
            return {
                "status": "online",
                "host": self.host,
                "models": models,
                "current_model": self.model,
                "model_ready": any(self.model in m for m in models),
            }
        except Exception as e:
            return {"status": "offline", "host": self.host, "error": str(e)}

    def ask(self, prompt: str, system: Optional[str] = None,
            use_history: bool = True) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        else:
            messages.append({
                "role": "system",
                "content": (
                    "أنت JARVIS، المساعد الذكي لنظام EsprieAether. "
                    "تتحدث العربيةبطولة. أنت خبير في الأمن السيبراني، "
                    "الذكاء الاصطناعي، وتحليل البيانات. أجب بدقة واحترافية."
                )
            })
        
        if use_history and self.history:
            messages.extend(self.history[-self.max_history:])
        
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
            }
        }
        
        try:
            r = requests.post(
                f"{self.host}/api/chat",
                json=payload,
                timeout=180
            )
            r.raise_for_status()
            data = r.json()
            response_text = data.get("message", {}).get("content", "")
            
            self.history.append({"role": "user", "content": prompt})
            self.history.append({"role": "assistant", "content": response_text})
            
            if len(self.history) > self.max_history * 2:
                self.history = self.history[-self.max_history * 2:]
            
            return response_text.strip()
            
        except requests.exceptions.Timeout:
            logger.error("Timeout after 180 seconds")
            return "⚠️ انتهاك 时间 (180 ثانية). يرجى تقليل طول الاستفسار أو زيادة timeout."
        except requests.exceptions.ConnectionError:
            logger.error("Connection error")
            return "⚠️ فشل الاتصال بـ Jarvis. تأكد من تشغيل Ollama."
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return f"⚠️ خطأ في الطلب: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return f"⚠️ خطأ غير متوقع: {str(e)}"