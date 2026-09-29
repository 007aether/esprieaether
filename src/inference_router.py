# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

"""
⚡ EsprieAether — Inference Router v5
توجيه ذكي + تحميل .env + Fallback سليم
"""
import os
import logging
from pathlib import Path
from enum import Enum
from dotenv import load_dotenv

ENV_PATH = Path.home() / "AETHER_V8" / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=str(ENV_PATH), override=True)

logger = logging.getLogger("inference_router")


class Complexity(Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    SENSITIVE = "sensitive"


SENSITIVE_KW = [
    "password", "secret", "private", "wallet", "key", "token", "seed", "mnemonic",
    "محفظة", "سر", "خاص", "مفتاح", "كلمة السر", "بذرة",
]

COMPLEX_KW = [
    "analyze", "design", "architect", "refactor", "debug", "optimize", "improve",
    "develop", "create system", "build framework", "plan", "strategy",
    "حلل", "صمم", "طوّر", "حسّن", "أصلح", "برمج", "أنشئ نظام", "ابن إطار",
    "اقترح", "خطة", "استراتيجية", "معقد",
]

MEDIUM_KW = [
    "write", "explain", "summarize", "translate", "describe", "compare",
    "اكتب", "اشرح", "لخص", "ترجم", "صف", "قارن", "مقالة", "تقرير",
    "كيف", "لماذا", "ما هو", "ما هي",
]

SIMPLE_KW = [
    "hi", "hello", "thanks", "yes", "no", "ok", "help",
    "مرحبا", "شكرا", "نعم", "لا", "حسنا", "أهلا", "السلام",
]


def _read_env_key(name: str) -> str:
    """يقرأ متغيرًا من .env مباشرة"""
    if not ENV_PATH.exists():
        return ""
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if line.startswith(f"{name}="):
            value = line.split("=", 1)[1].strip()
            return value.strip('"').strip("'")
    return ""


def _validate_key(key: str, provider: str) -> str:
    """يتحقق من صلاحية المفتاح"""
    if not key:
        raise ValueError(f"❌ {provider}: المفتاح فارغ")
    if not all(ord(c) < 128 for c in key):
        bad = [c for c in key if ord(c) > 127][:3]
        raise ValueError(f"❌ {provider}: المفتاح يحتوي على أحرف غير صالحة: {bad}")
    return key


def _get_providers():
    """يعيد خريطة المزودين"""
    return {
        Complexity.SIMPLE: {
            "provider": "groq",
            "model": _read_env_key("GROQ_MODEL") or "llama-3.1-70b-versatile",
            "api_key": _read_env_key("GROQ_API_KEY"),
            "base_url": _read_env_key("GROQ_BASE_URL") or "https://api.groq.com/openai/v1",
        },
        Complexity.MEDIUM: {
            "provider": "openrouter",
            "model": _read_env_key("OPENROUTER_MODEL") or "openai/gpt-4o-mini",
            "api_key": _read_env_key("OPENROUTER_API_KEY"),
            "base_url": _read_env_key("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1",
        },
        Complexity.COMPLEX: {
            "provider": "openrouter",
            "model": _read_env_key("OPENROUTER_MODEL") or "openai/gpt-4o-mini",
            "api_key": _read_env_key("OPENROUTER_API_KEY"),
            "base_url": _read_env_key("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1",
        },
        Complexity.SENSITIVE: {
            "provider": "ollama",
            "model": _read_env_key("OLLAMA_MODEL_BALANCED") or "qwen2.5:3b",
            "api_key": None,
            "base_url": (_read_env_key("OLLAMA_HOST") or "http://127.0.0.1:11434") + "/v1",
        },
    }


def analyze_complexity(task: str) -> Complexity:
    """يحلل تعقيد المهمة"""
    task_lower = task.lower().strip()
    words = task_lower.split()
    n_words = len(words)
    
    if any(kw in task_lower for kw in SENSITIVE_KW):
        return Complexity.SENSITIVE
    if any(kw in task_lower for kw in COMPLEX_KW):
        return Complexity.COMPLEX
    if n_words > 60:
        return Complexity.COMPLEX
    if any(kw in task_lower for kw in SIMPLE_KW) and n_words <= 5:
        return Complexity.SIMPLE
    if n_words <= 3:
        return Complexity.SIMPLE
    if any(kw in task_lower for kw in MEDIUM_KW):
        return Complexity.MEDIUM
    if n_words > 10:
        return Complexity.MEDIUM
    return Complexity.MEDIUM


def get_provider(task: str) -> dict:
    """يعيد المزود المناسب"""
    complexity = analyze_complexity(task)
    providers = _get_providers()
    provider = providers[complexity].copy()
    provider["complexity"] = complexity.value
    logger.info(f"🎯 Task → {provider['provider']} ({complexity.value})")
    return provider


def get_client(task: str):
    """يعيد (client, provider_info)"""
    from openai import OpenAI
    p = get_provider(task)
    
    if p["provider"] == "ollama":
        return OpenAI(base_url=p["base_url"], api_key="ollama"), p
    
    p["api_key"] = _validate_key(p["api_key"], p["provider"])
    return OpenAI(base_url=p["base_url"], api_key=p["api_key"]), p


def ask(task: str, system: str = "أنت مساعد ذكي") -> str:
    """دالة موحدة لإرسال مهمة"""
    from openai import OpenAI
    
    try:
        client, p = get_client(task)
    except Exception as e:
        logger.error(f"❌ {e}")
        return f"[ERROR] {e}"
    
    try:
        r = client.chat.completions.create(
            model=p["model"],
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": task},
            ],
            timeout=120,
        )
        return r.choices[0].message.content
    except Exception as e:
        logger.error(f"❌ {p['provider']} failed: {e}")
        
        # Fallback: جرّب Groq
        if p["provider"] != "groq":
            logger.info("🔄 Fallback → Groq")
            try:
                groq_key = _validate_key(_read_env_key("GROQ_API_KEY"), "groq")
                client2 = OpenAI(
                    base_url=_read_env_key("GROQ_BASE_URL") or "https://api.groq.com/openai/v1",
                    api_key=groq_key,
                )
                r = client2.chat.completions.create(
                    model=_read_env_key("GROQ_MODEL") or "llama-3.1-70b-versatile",
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": task},
                    ],
                    timeout=120,
                )
                return r.choices[0].message.content
            except Exception as e2:
                logger.error(f"❌ Groq fallback failed: {e2}")
                return f"[ERROR] {e2}"
        
        return f"[ERROR] {e}"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    
    print("═══ فحص الإعدادات ═══")
    for key in ["OPENROUTER_API_KEY", "GROQ_API_KEY", "OPENROUTER_MODEL", "GROQ_MODEL"]:
        v = _read_env_key(key)
        if v:
            ok = all(ord(c) < 128 for c in v)
            print(f"  ✅ {key}: {len(v)} حرف، ASCII={ok}")
        else:
            print(f"  ❌ {key}: فارغ")
    
    print("\n═══ اختبار التوجيه ═══")
    tests = [
        "مرحبا",
        "اكتب لي مقالة عن الذكاء الاصطناعي",
        "حلل أداء النظام واقترح تحسينات معقدة",
        "أرسل لي محفظتي الخاصة",
        "ما هو الطقس؟",
    ]
    for t in tests:
        p = get_provider(t)
        print(f"📝 {t[:45]:<45} → {p['provider']:<12} ({p['complexity']})")
    
    print("\n═══ اختبار فعلي (Groq) ═══")
    try:
        response = ask("قل مرحبا فقط")
        print(f"✅ الرد: {response[:100]}")
    except Exception as e:
        print(f"❌ {e}")
