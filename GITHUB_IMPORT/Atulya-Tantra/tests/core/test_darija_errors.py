"""Les erreurs du moteur et des fournisseurs doivent être en darija (J105)."""
from pathlib import Path

from tools.plugins.brain import engine, providers

SOURCES = (Path(engine.__file__), Path(providers.__file__))

ENGLISH_ERRORS = (
    "Could not get a valid reply",
    "returned an unexpected response",
    "returned an empty reply",
    "returned an unexpected stream",
    "returned HTTP",
    "Could not connect to Ollama",
    "No configured model provider could answer",
    "No configured model provider is available",
    "The model provider failed while generating a reply",
    "The model provider returned an empty reply",
)


def test_aucune_erreur_moteur_ne_reste_en_anglais():
    for source in SOURCES:
        text = source.read_text(encoding="utf-8")
        for phrase in ENGLISH_ERRORS:
            assert phrase not in text, f"{source.name}: {phrase}"


def test_les_erreurs_deflux_sont_en_arabe():
    for source in SOURCES:
        text = source.read_text(encoding="utf-8")
        assert any(word in text for word in ("توقف فجأة", "ما قدرش", "ما قدرتش", "فاضي")), source.name
