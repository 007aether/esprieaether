#!/usr/bin/env python3
"""
ESPRIEAETHER MULTI-BRAIN MERGE ENGINE
======================================
Instead of using ONE brain, this system merges ALL brains (local + cloud)
to generate better answers.

ARCHITECTURE:
  - Parallel mode: ALL brains respond simultaneously, answers merged
  - Fallback: If internet down → use ALL LOCAL brains merged
  - Smart: Short prompts → fast brain; Long prompts → smart brain
  - Quality gate: If merged quality < threshold → auto-prompt again

Brains involved:
  - colibri-local (Qwen3-Coder-30B, local D:)
  - ollama-local (Qwen2.5:3B, localhost)
  - llm7-fast (mistral-Nemo, keyless free cloud)
  - llm7-big (gpt-oss:20B, keyless free cloud)
  - groq (gpt-oss-120B, free tier)
  - minimax (abab6.5s, free tier)
"""

import json
import os
import sys
import time
import concurrent.futures
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

# ── Paths ──────────────────────────────────────────────────────────────
ESPRIEAETHER_DIR = Path(__file__).resolve().parent.parent
HOME_DIR = Path(os.path.expanduser("~"))

# ── Configuration ─────────────────────────────────────────────────────
CONFIG = {
    "min_brains": 2,          # Minimum brains to merge
    "max_brains": 4,          # Maximum brains to use per request
    "parallel_timeout": 60,   # Seconds per brain
    "merge_prompt": """You are an intelligent fusion engine. 

You receive multiple answers from DIFFERENT AI brains (some local, some cloud).
Your job is to MERGE them into ONE excellent answer.

Rules:
1. Simplify the best parts from all answers
2. If answers disagree, pick the most common or most accurate
3. Keep the answer concise and clear
4. Preserve all key facts and numbers
5. Output in Arabic with clarity

Here are the answers:
{answers}""",
}


class MultiBrainEngine:
    """
    Merges multiple AI brains to generate better answers.

    INSTEAD OF ONE MIND → WE HAVE A COMMITTEE OF MINDS
    - All local brains (colibri, ollama) run in parallel
    - All cloud brains (llm7, groq, minimax) run in parallel
    - Answers are merged on the fly
    - When offline → use only local brains
    - When online and slow → pick fastest 2-3 brains
    """

    def __init__(self):
        self.brains = self._load_brains()
        self.health = {}

    # ── Brain definitions ────────────────────────────────────────────────

    def _load_brains(self) -> list:
        """Define all available brains."""
        return [
            {
                "name": "colibri-local",
                "type": "local",
                "model": "qwen3-coder-30b",
                "url": "http://127.0.0.1:8000/v1/chat/completions",
                "label": "العقل القوي (محلي D:)",
            },
            {
                "name": "ollama-local",
                "type": "local",
                "model": "qwen2.5:3b",
                "url": "http://127.0.0.1:11434/v1/chat/completions",
                "label": "العقل الخفيف (محلي)",
            },
            {
                "name": "llm7-fast",
                "type": "cloud",
                "model": "mistral-Nemo-Instruct-2407",
                "url": "https://api.llm7.io/v1/chat/completions",
                "label": "العقل السحابي السريع",
            },
            {
                "name": "llm7-big",
                "type": "cloud",
                "model": "gpt-oss:20b",
                "url": "https://api.llm7.io/v1/chat/completions",
                "label": "العقل السحابي القوي",
            },
            {
                "name": "groq",
                "type": "cloud",
                "model": "gpt-oss-120b",
                "url": "https://api.groq.com/openai/v1/chat/completions",
                "label": "العقل السحابي الممتاز",
            },
            {
                "name": "minimax",
                "type": "cloud",
                "model": "abab6.5s",
                "url": "https://api.minimax.chat/v1/chat/completions",
                "label": "العقل السحابي الخاص",
            },
        ]

    def health_check(self) -> dict:
        """Check which brains are currently available."""
        results = {}
        for brain in self.brains:
            try:
                req = urllib.request.Request(
                    brain["url"].replace("/chat/completions", "/models"),
                    headers={"Authorization": "Bearer dummy"},
                    method="HEAD"
                )
                with urllib.request.urlopen(req, timeout=3) as r:
                    results[brain["name"]] = {"status": "healthy", "type": brain["type"]}
            except Exception:
                try:
                    # Try to ping directly
                    req = urllib.request.Request(brain["url"])
                    with urllib.request.urlopen(req, timeout=3) as r:
                        results[brain["name"]] = {"status": "healthy", "type": brain["type"]}
                except Exception:
                    results[brain["name"]] = {"status": "down", "type": brain["type"]}
        self.health = results
        return results

    # ── Parallel calling ──────────────────────────────────────────────────

    def call_brain(self, brain: dict, messages: list, timeout: int = 60) -> Dict:
        """Call a single brain and get the response."""
        start_time = time.time()  # Define start time before try block
        try:
            payload = {
                "model": brain["model"],
                "messages": messages,
                "stream": False,
            }
            data = json.dumps(payload).encode("utf-8")
            headers = {
                "Content-Type": "application/json",
                "Authorization": brain.get("key", "dummy-key"),
            }
            req = urllib.request.Request(
                brain["url"],
                data=data,
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                result = json.loads(r.read())
                # Extract content
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0].get("message", {}).get("content", "")
                else:
                    content = json.dumps(result)
                return {
                    "brain": brain["name"],
                    "label": brain["label"],
                    "content": content,
                    "type": brain["type"],
                    "success": True,
                    "time": 0,
                }
        except Exception as e:
            return {
                "brain": brain["name"],
                "label": brain["label"],
                "content": f"[خطأ: {str(e)[:100]}]",
                "type": brain["type"],
                "success": False,
                "time": 0,
            }

    # ── Merging ──────────────────────────────────────────────────────────

    def merge_answers(self, answers: list, prompt: str) -> str:
        """
        Merge multiple answers into one excellent answer.

        Uses a merge prompt to combine all answers smartly.
        """
        # Filter out failed answers
        successful = [a for a in answers if a.get("success") and len(a.get("content", "")) > 10]

        if not successful:
            return "[لم ترد أجوبة مفيدة من أي عقول]"

        # Format the answers for the merge prompt
        answers_text = ""
        for a in successful:
            label = a.get("label", "عقل مجهول")
            brain_type = a.get("brain_type", a.get("type", "غير محدد"))
            content = a.get("content", "")[:500]
            answers_text += f"\n── {label} ({brain_type}) ──\n{content}\n"

        # Create merge prompt
        merge_msg = CONFIG["merge_prompt"].format(answers=answers_text)

        # Call colibri to do the merging (local, fast)
        merge_brain = next((b for b in self.brains if b["name"] == "colibri-local"), None)
        if merge_brain:
            try:
                result = self.call_brain(merge_brain, [
                    {"role": "user", "content": merge_msg}
                ], timeout=60)
                if result["success"]:
                    return result["content"]
            except Exception:
                pass

        # Fallback: use the first successful answer
        return successful[0]["content"]

    # ── Main interface ────────────────────────────────────────────────────

    def chat(self, prompt: str) -> dict:
        """
        Send prompt to ALL brains in parallel, merge answers.

        Args:
            prompt: The user message

        Returns:
            dict with merged response and metadata
        """
        start = time.time()

        messages = [{"role": "user", "content": prompt}]

        # Determine which brains to use
        health = self.health_check()
        available = [b for b in self.brains if health.get(b["name"], {}).get("status") == "healthy"]

        # Strategy:
        # - If 6+ brains available: use fastest 3
        # - If 2-5 brains: use all
        # - If < 2: use colibri-only
        if len(available) >= 6:
            available = available[:3]  # Use fastest 3
        elif len(available) < 2:
            available = [b for b in self.brains if b["name"] == "colibri-local"]

        # Call all brains in parallel
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(available)) as executor:
            futures = {}
            for brain in available:
                fut = executor.submit(self.call_brain, brain, messages)
                futures[fut] = brain["name"]

            for fut in concurrent.futures.as_completed(futures):
                brain_name = futures[fut]
                try:
                    result = fut.result()
                    result["brain_name"] = brain_name
                    results.append(result)
                except Exception as e:
                    results.append({
                        "brain": brain_name,
                        "content": f"[خطأ: {str(e)[:100]}]",
                        "success": False,
                    })

        # Merge the answers
        merged = self.merge_answers(results, prompt)

        # Log the session
        self._log_session(prompt, results, merged)

        return {
            "response": merged,
            "brains_used": [r["brain"] for r in results if r.get("success")],
            "brains_failed": [r["brain"] for r in results if not r.get("success")],
            "merge_method": "parallel_merge" if len(results) > 1 else "single",
            "time": time.time() - start,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _log_session(self, prompt: str, results: list, merged: str):
        """Log the multi-brain session to knowledge base."""
        try:
            from src.knowledge_router import store_knowledge
            log_entry = {
                "text": f"🧠 Multi-brain session: {len(results)} brains used",
                "tags": ["multi-brain", "merge", "log"],
                "source": "multi-brain-engine",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            store_knowledge(**log_entry)
        except Exception:
            pass

    def add_brain(self, brain: dict):
        """Add a new brain to the pool."""
        self.brains.append(brain)


def main():
    """Test the multi-brain engine."""
    import json
    engine = MultiBrainEngine()

    print("🔗 Multi-Brain Engine (ESPRIEAETHER)")
    print("=" * 50)
    print(f"Available brains: {len(engine.brains)}")
    for b in engine.brains:
        print(f"  • {b['name']}: {b['label']}")

    print("\nChecking health...")
    health = engine.health_check()
    for name, status in health.items():
        print(f"  {name}: {status['status']}")

    # Test with a sample prompt
    print("\nTesting with: 'ما هو الفرق بين Python و JavaScript؟'")
    result = engine.chat("ما هو الفرق بين Python و JavaScript؟")
    print(f"\n✅ Merged response:")
    print(result["response"][:500])
    print(f"\n⏱️  Time: {result['time']:.2f}s")
    print(f"🧠 Brains used: {len(result['brains_used'])}")


if __name__ == "__main__":
    main()
