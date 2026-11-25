"""Les acquittements instantanés d'Atulya doivent rester en darija (J105)."""
import re
from types import SimpleNamespace

from tools.plugins.brain import engine


ALL_PHRASES = (*[phrase for _, phrase in engine._INTENT_FILLERS], *engine._FILLERS.values(), engine.DEFAULT_FILLER)


def test_instant_ack_status_est_en_darija():
    ack = engine.instant_ack("Jarvis, quick status report on all systems.")
    assert ack.strip() == "كنفحص الأنظمة."
    assert re.search(r"[\u0600-\u06FF]", ack)


def test_instant_ack_comprend_les_mots_darija():
    assert engine.instant_ack("شنو حالة النظام؟").strip() == "كنفحص الأنظمة."
    assert engine.instant_ack("شنو الطقس اليوم؟").strip() == "كنشوف الطقس."


def test_aucun_acquittement_ne_reste_en_anglais():
    for phrase in ALL_PHRASES:
        if not phrase:
            continue
        assert re.search(r"[\u0600-\u06FF]", phrase), phrase
        assert not re.search(r"[A-Za-z]", phrase), phrase


def test_filler_d_outil_inconnu_est_en_darija():
    calls = [SimpleNamespace(name="tool_inconnu")]
    assert engine._tool_filler(calls) == "لحظة من فضلك. "


def test_source_des_acquittements_sans_anglais():
    source = (engine.__file__ and open(engine.__file__, encoding="utf-8").read()) or ""
    for English in ("Checking the weather", "Checking the systems", "Pulling up the headlines",
                    "Looking through our past conversations", "One moment."):
        assert English not in source
