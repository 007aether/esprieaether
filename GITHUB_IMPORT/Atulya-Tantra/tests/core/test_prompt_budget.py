"""Le prompt reste court, non redondant et sans promesse d'état inventée."""
from __future__ import annotations

from atulya.persona import EVIDENCE_RULE, build_system_prompt
from atulya.profiles import DEFAULTS, profile_instructions


def test_persona_and_profile_fit_a_small_token_budget() -> None:
    persona = build_system_prompt("Atulya")
    profile = profile_instructions(dict(DEFAULTS))
    assert len(persona) <= 1100
    assert len(profile) <= 550
    assert len(persona) + 2 + len(profile) <= 1600


def test_darija_rule_is_stated_exactly_once() -> None:
    persona = build_system_prompt("Atulya")
    assert persona.count("الدارجة المغربية") == 1
    assert persona.count("بحروف عربية") == 1
    assert persona.count("mishears") == 1
    assert persona.count("الغلط") == 0


def test_single_sentence_length_rule() -> None:
    persona = build_system_prompt("Atulya")
    profile = profile_instructions(dict(DEFAULTS))
    assert "1–2 sentences" in persona
    assert "1-3 sentences" not in profile


def test_status_rule_is_central_and_language_default_is_untouched() -> None:
    persona = build_system_prompt("Atulya")
    assert EVIDENCE_RULE in persona
    assert "tool" in EVIDENCE_RULE.lower()
    assert DEFAULTS["language"] == "auto"
