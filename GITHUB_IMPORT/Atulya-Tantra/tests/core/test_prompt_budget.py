"""Le prompt injecté reste court : le petit modèle local doit répondre avant 12 s."""
import json

from atulya.evolution import lessons_for_prompt
from atulya.recent_actions import recent_actions


def test_lessons_injection_est_plafonnee(tmp_path):
    lessons = tmp_path / "lessons.json"
    items = [
        {"id": f"{i:010d}", "user_id": "admin", "text": f"Never do thing number {i}: " + "blah " * 60}
        for i in range(8)
    ]
    lessons.write_text(json.dumps({"items": items}), encoding="utf-8")
    prompt = lessons_for_prompt(tmp_path, "admin")
    assert len(prompt) <= 500
    assert "thing number 7" in prompt
    assert "thing number 0" not in prompt


def test_actions_injection_est_plafonnee(tmp_path):
    rows = [
        json.dumps({"user_id": "admin", "tool": f"tool_{i}", "channel": "web",
                    "at": "2026-11-27T00:00:00+00:00", "outcome": "ok: " + "details " * 40})
        for i in range(20)
    ]
    (tmp_path / "audit.jsonl").write_text("\n".join(rows), encoding="utf-8")
    prompt = recent_actions(tmp_path)
    assert len(prompt) <= 500
    assert "tool_19" in prompt
    assert "tool_0:" not in prompt
