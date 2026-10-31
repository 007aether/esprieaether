#!/usr/bin/env python3
"""
jarvis_agent.py — AETHER-JARVIS: الوكيل الوحيد للحوار
=====================================================
Jarvis = الواجهة الوحيد للحوار + الشخصية + ذاكرة Obsidian.

دورة العمل:
  1. نكتب (Telegram / Hermes / dashboard)
  2.jarvis크림how detects intent (نظام / بحث / تداول / دردشة / كود)
  3. يعطي المهمة للعقل المناسب (Fast / Mid / Heavy) أو للـ council
  4. يرجع جواباً واحداً بصوت JARVIS
  5. يسجل الجلسة فـ Obsidian (Jarvis/Daily, Jarvis/Memory, Jarvis/Sessions)

الاستخدام:
  from src.jarvis.agent import JarvisAgent
  jarvis = JarvisAgent()
  reply = jarvis.ask("مرحباً")
"""

import logging
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

from multi_brain_engine import MultiBrainEngine
from jarvis.obsidian import ObsidianLogger, resolve_vault

# ── Paths ────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "logs"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Logging ──────────────────────────────────────────────────────────
logger = logging.getLogger("jarvis_agent")
logger.setLevel(logging.INFO)
# Prevent duplicate handlers if imported multiple times
if not logger.handlers:
    _handler = logging.FileHandler(DATA_DIR / "jarvis_agent.log", encoding="utf-8")
    _handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    logger.addHandler(_handler)
    _handler_stdout = logging.StreamHandler(sys.stdout)
    _handler_stdout.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
    logger.addHandler(_handler_stdout)


# ── Intent detection ─────────────────────────────────────────────────
def detect_intent(text: str) -> dict:
    """Detect the user's intent and return (intent, confidence, matched_keywords)."""
    t = text.lower().strip()

    # Commands that must route to a specific agent / system action
    COMMAND_PATTERNS = {
        "system": [r"^تبدأ|شغّل|أبدأ|start|run|تشغيل|أعد"],
        "trade": [r"تداول|trade|ترجر|سوق|سعر|سوي|market|price|تداول|exchange"],
        "research": [r"ابحث|بحث|لخص|تلخيص|research|analyze|summarize|تحليل|استطلاع"],
        "coden": [r"كود|code|اكتب|برنامج|function|script|py|python|java|تشغي"],
        "security": [r"أمن|security|أخترق|اختراق|فحص|برنامج|penetrate|hack|أمن سيبراني"],
        "creative": [r"قصص|قصة|رسم|أبي|خيال|خيالي|creative|story|art|رسم"],
        "brain": [r"عقول|دماغ|brain|أعقل|أفضل عقول"],
        "memory": [r"ذاكرة|memory|ذاكر|\+", r"تذكر|مذاكرت|مذاكرة"],
        "general": [],  # default
    }

    # Default intent: conversation
    intent = "general"
    keywords = []

    # Check each command category
    for cat, patterns in COMMAND_PATTERNS.items():
        if cat == "general":
            continue
        for pat in patterns:
            if re.search(pat, t):
                intent = cat
                keywords.extend(re.findall(pat, t))
                break

    confidence = 0.9 if intent != "general" else 0.4

    return {
        "intent": intent,
        "confidence": confidence,
        "keywords": list(set(keywords)),
        "text": text,
    }


# ── Jarvis agent ──────────────────────────────────────────────────────
class JarvisAgent:
    """
    JARVIS agent: one interface, three brains, permanent Obsidian memory.
    """

    def __init__(self, model: str = "ollama-local", log_to_obsidian: bool = True):
        self.model = model
        self.log_to_obsidian = log_to_obsidian
        self.logger = logging.getLogger("jarvis_agent")

        # Multi-brain engine (the routing brain)
        self.brain_engine = MultiBrainEngine()

        # Obsidian logger
        self.log = ObsidianLogger()

        # Session state
        self.session_id = str(uuid.uuid4())[:8]
        self.history = []
        self.max_history = 20

        # Intent cache (to remember context across messages)
        self.intent_cache = {}

        logger.info(f"Jarvis agent started (session {self.session_id})")

    # ── Core methods ────────────────────────────────────────────────────

    def ask(self, prompt: str, system: str = None, user: str = "user") -> str:
        """
        Main entry point. Receives a message and returns a Jarvis answer.
        """
        ts = datetime.now().isoformat()
        self.logger.info(f"[Session {self.session_id}] User: {prompt}")

        # 1) Detect intent
        intent = detect_intent(prompt)
        self.logger.info(f"[Session {self.session_id}] Intent: {intent['intent']} (confidence {intent['confidence']:.2f})")

        # 2) Route to the brain (based on intent + RAM-aware cascade)
        result = self._route(prompt, intent)

        # 3) Log the session to Obsidian
        if self.log_to_obsidian:
            self._log_session(prompt, result)

        # 4) Return the answer
        return result["response"]

    def _route(self, prompt: str, intent: dict) -> dict:
        """
        Route the prompt to the right brain(s).
        Returns: {response, brains_used, method, raw}
        """
        mode = "cascade"
        brains_to_use = []

        # ── Command routing ──
        if intent["intent"] == "system":
            # System commands: use the local merge brain (fast)
            brains_to_use = ["ollama-local"]
            mode = "jarvis"
        elif intent["intent"] == "trade":
            # Trading: use the heavy brain (deep analysis) - but check RAM
            if self.brain_engine.ram_free_gb >= 8:
                brains_to_use = ["ollama-unc-heavy", "ollama-unc-mid"]
            else:
                brains_to_use = ["ollama-unc-mid"]
            mode = "jarvis"
        elif intent["intent"] == "research":
            # Research: use the council (parallel merge) for comprehensive answers
            brains_to_use = ["ollama-unc-fast", "ollama-unc-mid"]
            mode = "parallel"
        elif intent["intent"] == "coden":
            # Code: use the fast brain + heavy for complex tasks
            if self.brain_engine.ram_free_gb >= 8:
                brains_to_use = ["ollama-unc-fast", "ollama-unc-heavy"]
            else:
                brains_to_use = ["ollama-unc-fast"]
            mode = "jarvis"
        elif intent["intent"] == "security":
            # Security: use the heavy brain for deep analysis
            brains_to_use = ["ollama-unc-heavy"]
            mode = "jarvis"
        elif intent["intent"] == "creative":
            # Creative: use the fast brain
            brains_to_use = ["ollama-unc-fast"]
            mode = "jarvis"
        elif intent["intent"] == "brain":
            # User asks about brains: use the local merge brain
            brains_to_use = ["ollama-local"]
            mode = "jarvis"
        else:
            # General conversation: cascade through all three
            brains_to_use = ["ollama-unc-fast", "ollama-unc-mid", "ollama-unc-heavy"]
            mode = "cascade"

        # Run the engine
        result = self.brain_engine.chat(prompt, mode=mode)

        # Filter to only the brains we want
        brains_used = [r["brain"] for r in result["brains_used"]]
        desired = [b for b in brains_to_use if b in brains_used]
        result["brains_used"] = desired if desired else result.get("brains_used", [])

        self.logger.info(f"[Session {self.session_id}] Routed to: {result['brains_used']} via {mode}")
        return result

    def _log_session(self, prompt: str, result: dict):
        """Log the entire session to Obsidian."""
        session_id = self.session_id
        prompt = prompt[:200]
        answer = result.get("response", "")[:500]
        brains = result.get("brains_used", [])
        method = result.get("merge_method", "unknown")

        # Write full transcript
        self.log.session_full(
            session_id=session_id,
            prompt=prompt,
            answer=answer,
            brains=brains,
            method=method,
            notes=f"Intent: {detect_intent(prompt)['intent']}",
        )

        # Update daily log with the new session
        # (the _log_session is called by the engine's _log_session; here we
        #  add a concise summary to the day file)
        self.log.session_end("user", feedback="session logged")

        # If this is a decision, remember it
        intent = detect_intent(prompt)
        if intent["intent"] in ("trade", "research", "coden", "security", "system"):
            self.log.decision(
                decision=answer[:200],
                context=prompt[:200],
                reason="Jarvis routed and answered via " + method,
            )


# ── Convenience functions ─────────────────────────────────────────────
def ask(prompt: str, model: str = "ollama-local", log: bool = True) -> str:
    """Quick one-shot ask."""
    jarvis = JarvisAgent(model=model)
    return jarvis.ask(prompt, log_to_obsidian=log)


def main():
    """Simple CLI for testing."""
    import sys

    jarvis = JarvisAgent()

    print("=" * 50)
    print("  JARVIS — الباب الوحيد للحوار")
    print("  (اكتب 'خروج' للإنهاء)")
    print("=" * 50)

    for line in sys.stdin:
        prompt = line.strip()
        if prompt.lower() in ("exit", "خروج", "quit", "q"):
            break
        if not prompt:
            continue
        try:
            answer = jarvis.ask(prompt)
            print(f"\nJarvis: {answer}\n")
        except Exception as e:
            print(f"\nJarvis: ⚠️ خطأ: {e}\n")


if __name__ == "__main__":
    main()
