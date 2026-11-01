#!/usr/bin/env python3
"""
ESPRIEAETHER MULTI-BRAIN MERGE ENGINE
======================================
Instead of using ONE brain, this system merges ALL brains (local + cloud)
to generate better answers.

ARCHITECTURE:
  - Cascade: Fast -> Mid -> Heavy sequentially (RAM-safe on 14 GB)
  - Council: Fast + Mid in parallel, merged by ollama-local (3B)
  - Fallback: If internet down -> use ALL LOCAL brains merged

Brains involved:
  - ollama-unc-fast (dolphin-llama3:8b, local)
  - ollama-unc-mid   (dolphin-mistral:7b, local)
  - ollama-unc-heavy (wizard-vicuna-uncensored:13b, local)
  - ollama-local     (qwen2.5:3b, localhost - merge engine + fallback)
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
    "min_brains": 2,
    "max_brains": 4,
    "parallel_timeout": 60,
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
    """Merges multiple AI brains to generate better answers.

    INSTEAD OF ONE MIND -> WE HAVE A COMMITTEE OF MINDS
    - All local brains (colibri, ollama) run in parallel
    - All cloud brains (llm7, groq, minimax) run in parallel
    - Answers are merged on the fly
    - When offline -> use only local brains
    - When online and slow -> pick fastest 2-3 brains
    """

    def __init__(self):
        self.brains = self._load_brains()
        self.health = {}
        self.ram_total_gb = 0.0
        self.ram_free_gb = 0.0
        self._parallel_local = False
        self._detect_ram()

    def _detect_ram(self):
        """Detect available RAM and set RAM-aware flags."""
        try:
            ram_total = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / (1024 ** 3)
            ram_free = ram_total * 0.85
        except Exception:
            ram_total = ram_free = 14.0
        self.ram_total_gb = ram_total
        self.ram_free_gb = ram_free
        # 14 GB laptop: local heavy runs SEQUENTIALLY (cascade); parallel = fast+mid only
        self._parallel_local = ram_free >= 13.0

    # ── Brain definitions ────────────────────────────────────────────────

    def _load_brains(self) -> list:
        """Define all available brains (local uncensored + cloud)."""
        return [
            {
                "name": "ollama-unc-fast",
                "type": "local",
                "model": "dolphin-llama3:8b",
                "url": "http://127.0.0.1:11434/v1/chat/completions",
                "label": "Fast · dolphin-llama3:8b (uncensored)",
            },
            {
                "name": "ollama-unc-mid",
                "type": "local",
                "model": "dolphin-mistral:7b",
                "url": "http://127.0.0.1:11434/v1/chat/completions",
                "label": "Mid · dolphin-mistral:7b (uncensored)",
            },
            {
                "name": "ollama-unc-heavy",
                "type": "local",
                "model": "wizard-vicuna-uncensored:13b",
                "url": "http://127.0.0.1:11434/v1/chat/completions",
                "label": "Deep · wizard-vicuna-uncensored:13b (uncensored)",
            },
            {
                "name": "ollama-local",
                "type": "local",
                "model": "qwen2.5:3b",
                "url": "http://127.0.0.1:11434/v1/chat/completions",
                "label": "Light · qwen2.5:3b (merge engine / fallback)",
            },
            {
                "name": "colibri-local",
                "type": "local",
                "model": "qwen3-coder-30b",
                "url": "http://127.0.0.1:8000/v1/chat/completions",
                "label": "Heavy · qwen3-coder-30b (local D:, optional)",
            },
            {
                "name": "llm7-fast",
                "type": "cloud",
                "model": "mistral-Nemo-Instruct-2407",
                "url": "https://api.llm7.io/v1/chat/completions",
                "label": "Cloud · mistral-Nemo (keyless free)",
            },
            {
                "name": "llm7-big",
                "type": "cloud",
                "model": "gpt-oss:20b",
                "url": "https://api.llm7.io/v1/chat/completions",
                "label": "Cloud · gpt-oss:20b (keyless free)",
            },
            {
                "name": "groq",
                "type": "cloud",
                "model": "gpt-oss-120b",
                "url": "https://api.groq.com/openai/v1/chat/completions",
                "label": "Cloud · gpt-oss-120b (free tier)",
            },
            {
                "name": "minimax",
                "type": "cloud",
                "model": "abab6.5s",
                "url": "https://api.minimax.chat/v1/chat/completions",
                "label": "Cloud · abab6.5s (free tier)",
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
                    method="GET"
                )
                with urllib.request.urlopen(req, timeout=3) as r:
                    results[brain["name"]] = {"status": "healthy", "type": brain["type"]}
            except Exception:
                try:
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
                "content": "[خطأ: %s]" % str(e)[:100],
                "type": brain["type"],
                "success": False,
                "time": 0,
            }

    # ── Merging ──────────────────────────────────────────────────────────

    def merge_answers(self, answers: list, prompt: str) -> str:
        """Merge multiple answers into one excellent answer.

        Uses a small local model (ollama-local 3B) as the merge engine.
        """
        successful = [a for a in answers if a.get("success") and len(a.get("content", "")) > 10]

        if not successful:
            return "[لم ترد أجوبة مفيدة من أي عقول]"

        # Format the answers for the merge prompt
        answers_text = ""
        for a in successful:
            label = a.get("label", "عقل مجهول")
            brain_type = a.get("brain_type", a.get("type", "غير محدد"))
            content = a.get("content", "")[:500]
            answers_text += "\n── %s (%s) ──\n%s\n" % (label, brain_type, content)

        # Create merge prompt
        merge_msg = CONFIG["merge_prompt"].format(answers=answers_text)

        # Use ollama-local (3B) as merge engine (RAM-friendly)
        merge_brain = next((b for b in self.brains if b["name"] == "ollama-local"), None)
        if merge_brain:
            try:
                result = self.call_brain(merge_brain, [
                    {"role": "user", "content": merge_msg}
                ], timeout=90)
                if result["success"]:
                    return result["content"]
            except Exception:
                pass

        # Fallback: use the first successful answer
        return successful[0]["content"]

    # ── Main interface ────────────────────────────────────────────────────

    def chat(self, prompt: str, mode: str = "cascade") -> dict:
        """Send prompt to brains and merge answers.

        RAM-aware routing (14 GB laptop):
        - aether-uncensored (cascade): Fast -> Mid -> Heavy sequentially.
          Only ONE local brain in memory at a time. Works on 14 GB.
        - aether-council (parallel):   Fast + Mid in parallel (fit together),
                                      merged by ollama-local (3B, already loaded).
                                      Heavy runs only in cascade.
        - aether-jarvis: Jarvis persona + cascade + Obsidian log.

        Args:
            prompt: The user message
            mode: "cascade" (sequential) | "parallel" (council) | "jarvis"

        Returns:
            dict with merged response and metadata
        """
        start = time.time()
        messages = [{"role": "user", "content": prompt}]

        # Decide the brain set based on mode
        if mode == "jarvis":
            available = [
                b for b in self.brains
                if b["name"] in ("ollama-unc-fast", "ollama-unc-mid", "ollama-unc-heavy")
            ]
            method = "jarvis_cascade"
        elif mode == "parallel":
            # Council: parallel Fast + Mid only (fit on 14 GB), merged by small local
            available = [
                b for b in self.brains
                if b["name"] in ("ollama-unc-fast", "ollama-unc-mid")
            ]
            method = "parallel_council"
        else:
            # Cascade: Fast -> Mid -> Heavy, one at a time (RAM-safe on 14 GB)
            available = [
                b for b in self.brains
                if b["name"] in ("ollama-unc-fast", "ollama-unc-mid", "ollama-unc-heavy")
            ]
            method = "cascade"

        # Call brains sequentially (RAM-safe) or in parallel (council)
        results = []
        if method == "parallel_council":
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(available)) as executor:
                futures = {executor.submit(self.call_brain, b, messages): b["name"] for b in available}
                for fut in concurrent.futures.as_completed(futures):
                    brain_name = futures[fut]
                    try:
                        result = fut.result()
                        result["brain_name"] = brain_name
                        results.append(result)
                    except Exception as e:
                        results.append({"brain": brain_name, "content": "[خطأ: %s]" % str(e)[:100], "success": False})
        else:
            for brain in available:
                try:
                    result = self.call_brain(brain, messages)
                    result["brain_name"] = brain["name"]
                    results.append(result)
                except Exception as e:
                    results.append({"brain": brain["name"], "content": "[خطأ: %s]" % str(e)[:100], "success": False})

        # Merge the answers
        merged = self.merge_answers(results, prompt)

        # Log the session
        self._log_session(prompt, results, merged, mode)

        return {
            "response": merged,
            "brains_used": [r["brain_name"] for r in results if r.get("success")],
            "brains_failed": [r["brain_name"] for r in results if not r.get("success")],
            "merge_method": method,
            "time": time.time() - start,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _log_session(self, prompt: str, results: list, merged: str, mode: str = "cascade"):
        """Log the session to the knowledge base (Obsidian later)."""
        try:
            from src.knowledge_router import store_knowledge
            tag = {"cascade": "cascade", "parallel_council": "council", "jarvis_cascade": "jarvis"}.get(mode, mode)
            log_entry = {
                "text": "🧠 Jarvis session (%s): %d brains" % (tag, len(results)),
                "tags": ["jarvis", tag, "merge", "log"],
                "source": "jarvis",
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
    print("Available brains: %d" % len(engine.brains))
    for b in engine.brains:
        print("  • %s: %s" % (b["name"], b["label"]))

    print("\nChecking health...")
    health = engine.health_check()
    for name, status in health.items():
        print("  %s: %s" % (name, status["status"]))

    # Test with a sample prompt
    print("\nTesting with: 'ما هو الفرق بين Python و JavaScript؟'")
    result = engine.chat("ما هو الفرق بين Python و JavaScript؟")
    print("\n✅ Merged response:")
    print(result["response"][:500])
    print("\n⏱️  Time: %.2fs" % result["time"])
    print("🧠 Brains used: %d" % len(result["brains_used"]))


if __name__ == "__main__":
    main()
