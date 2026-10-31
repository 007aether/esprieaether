#!/usr/bin/env python3
"""
obsidian.py — JARVIS Obsidian vault logger
========================================
JARVIS writes EVERY session to the Obsidian vault so memory is permanent.

Vault layout:
  Jarvis/Daily/YYYY-MM-DD.md          — daily session logs
  Jarvis/Memory/decisions.md          — permanent decisions & learnings
  Jarvis/Sessions/<uuid>.md           — full session transcripts

Usage:
  from src.jarvis.obsidian import ObsidianLogger
  log = ObsidianLogger()
  log.session_start("user", "Hello")
  log.answer("Jarvis", "Hello! How can I help?")
  log.session_end("user", "Goodbye")
"""

import os
import re
import uuid
from datetime import datetime
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
HOME_DIR = Path(os.path.expanduser("~"))
VAULT = HOME_DIR / "ObsidianVault" / "EsprieAether"

# Default: /tmp/jarvis_vault (don't touch the real vault during development)
DEV_VAULT = os.getenv("JARVIS_VAULT", str(Path("/tmp/jarvis_vault")))

# Tag that means "this is a decision/judgment"
DECISION_TAGS = {"قرار", "قررت", "قرارvvvvvvvv", "قدم", "قررت ان", "اتخذت", "قررت ان اتخذت", "قررت ان لا", "سأ", "سوف", "plans", "plan"}


def resolve_vault() -> Path:
    """Return the vault path: dev path in tests, real vault in production."""
    if os.getenv("JARVIS_DEV", "").lower() in ("1", "true", "yes"):
        return Path(DEV_VAULT)
    return VAULT


class ObsidianLogger:
    """Write JARVIS sessions to Obsidian vault."""

    def __init__(self, vault: Path | None = None):
        self.vault = resolve_vault() if vault is None else Path(vault)
        self._ensure_structure()

    # ── internal ────────────────────────────────────────────────────────

    def _ensure_structure(self):
        """Create the Jarvis vault directories."""
        (self.vault / "Jarvis" / "Daily").mkdir(parents=True, exist_ok=True)
        (self.vault / "Jarvis" / "Memory").mkdir(parents=True, exist_ok=True)
        (self.vault / "Jarvis" / "Sessions").mkdir(parents=True, exist_ok=True)

    def _write(self, path: Path, content: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        # Append mode: preserve history (daily logs accumulate)
        mode = "a" if path.exists() else "w"
        with open(path, "a" if mode == "a" else "w", encoding="utf-8") as f:
            f.write(content)
            if not content.endswith("\n"):
                f.write("\n")

    def _today_file(self) -> Path:
        today = datetime.now().strftime("%Y-%m-%d")
        return self.vault / "Jarvis" / "Daily" / f"{today}.md"

    # ── public API ──────────────────────────────────────────────────────

    def session_start(self, user: str, prompt: str):
        """Log session start."""
        ts = datetime.now().isoformat()
        entry = (
            f"## Session start {ts}\n"
            f"- **User:** {user}\n"
            f"- **Prompt:** {prompt}\n"
            f"- **Jarvis:** (analyzing intent)\n"
            f"- **Brain:** (routing)\n\n"
        )
        self._write(self._today_file(), entry)

    def answer(self, jarvis: str, response: str, brains: list | None = None, method: str = "unknown"):
        """Log Jarvis's answer."""
        ts = datetime.now().isoformat()
        brain_str = " ".join(f"`{b}`" for b in brains) if brains else ""
        entry = (
            f"- **Jarvis:** {jarvis}\n"
            f"- **Response:** {response}\n"
            f"- **Brains:** {brain_str}\n"
            f"- **Method:** {method}\n\n"
        )
        self._write(self._today_file(), entry)

    def session_end(self, user: str, feedback: str = ""):
        """Log session end."""
        ts = datetime.now().isoformat()
        entry = f"- **End:** {ts}\n"
        if feedback:
            entry += f"- **Feedback:** {feedback}\n"
        self._write(self._today_file(), entry)

    def decision(self, decision: str, context: str = "", reason: str = ""):
        """Log a permanent decision to Memory/decisions.md."""
        ts = datetime.now().isoformat()
        file = self.vault / "Jarvis" / "Memory" / "decisions.md"
        tags = " ".join(t for t in DECISION_TAGS if t in decision.lower() or t in decision)
        entry = (
            f"## {ts}\n"
            f"- **Decision:** {decision}\n"
            f"- **Context:** {context}\n"
            f"- **Reason:** {reason}\n"
            f"- **Tags:** {tags}\n\n"
        )
        self._write(file, entry)

    def session_full(self, session_id: str, prompt: str, answer: str, brains: list, method: str, notes: str = ""):
        """Write a full session transcript to Sessions/<uuid>.md."""
        ts = datetime.now().isoformat()
        file = self.vault / "Jarvis" / "Sessions" / f"{session_id}.md"
        content = (
            f"# Session {session_id}\n\n"
            f"- **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"- **User:** {prompt[:100]}\n"
            f"- **Method:** {method}\n"
            f"- **Brains:** {', '.join(brains) if brains else 'unknown'}\n"
            f"- **Notes:** {notes}\n\n"
            f"## Prompt\n\n{prompt}\n\n"
            f"## Answer\n\n{answer}\n\n"
            f"## Obsidian Log\n\nSee: {file.name}\n"
        )
        self._write(file, content)

    def memory_retrieve(self, query: str) -> str:
        """Retrieve relevant memories from memory/decisions.md (simple keyword search)."""
        decisions_file = self.vault / "Jarvis" / "Memory" / "decisions.md"
        if not decisions_file.exists():
            return ""
        text = decisions_file.read_text(encoding="utf-8", errors="ignore")
        query = query.lower()
        lines = text.split("\n")
        matches = []
        for i, line in enumerate(lines):
            if query in line.lower():
                matches.append(line.strip())
                # Include next 3 lines for context
                for j in range(1, min(4, len(lines) - i)):
                    if lines[i + j].strip():
                        matches.append("    " + lines[i + j].strip())
        return "\n".join(matches[:15])
