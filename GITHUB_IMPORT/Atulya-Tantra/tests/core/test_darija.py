"""Darija is the default contract for understanding and replying."""
from __future__ import annotations

import os

from atulya.persona import build_system_prompt
from atulya.profiles import CHOICES, profile_instructions, validate
from tools.plugins.voice.local import _PROFILE_LANGUAGES


def test_reply_is_darija_by_default_without_an_env_flag() -> None:
    previous = os.environ.pop("ATULYA_FORCE_DARIJA", None)
    try:
        prompt = build_system_prompt("Atulya")
    finally:
        if previous is not None:
            os.environ["ATULYA_FORCE_DARIJA"] = previous
    assert "الدارجة المغربية" in prompt
    assert "بحروف عربية" in prompt


def test_prompt_understands_mixed_speech_but_never_switches_language() -> None:
    prompt = build_system_prompt("Atulya")
    assert "الدارجة" in prompt
    assert "فرنسية" in prompt or "فرانسوية" in prompt
    assert "إنجليزية" in prompt or "الإنجليزية" in prompt
    assert "ما تبدّلش اللغة" in prompt


def test_darija_is_a_selectable_stt_language() -> None:
    assert validate("language", "darija") == "darija"
    assert "darija" in CHOICES["language"]
    assert _PROFILE_LANGUAGES["darija"] == "ar"
    instructions = profile_instructions({"language": "darija", "tone": "atulya", "length": "short"})
    assert "الدارجة المغربية" in instructions
    assert "Reply in Arabic." not in instructions
