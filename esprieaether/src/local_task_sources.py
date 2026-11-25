"""Sources réelles pour les tâches autonomes et la page /analytics.

Règle : si un module n'existe pas, on dit `unavailable`. On ne fabrique jamais
des compteurs à zéro qui font croire qu'un système a tourné.
"""

import importlib.util
from datetime import datetime, timezone


def module_status(name: str) -> dict:
    """État d'import d'un module optionnel, sans l'importer."""
    try:
        if importlib.util.find_spec(name) is not None:
            return {"status": "available", "source": name}
    except (ImportError, ValueError):
        pass
    return {"status": "unavailable", "source": name, "reason": "module not installed"}


def semantic_memory_snapshot(remember_cycle: bool = False) -> dict:
    """Mémoire sémantique réelle : adaptateur sur vector_memory_agent (déjà présent)."""
    try:
        from vector_memory_agent import VectorMemory

        memory = VectorMemory()
        if remember_cycle:
            memory.remember(
                f"دورة {datetime.now(timezone.utc).isoformat()}",
                kind="conversation",
                source="autonomous_loop",
                importance=0.3,
            )
        return {
            "status": "ok",
            "source": "vector_memory_agent",
            "total": memory.stats()["total"],
        }
    except Exception as exc:  # pragma: no cover - dépend de l'état du disque
        return {"status": "unavailable", "source": "vector_memory_agent", "reason": type(exc).__name__}


def analytics_snapshot() -> dict:
    """Statistiques d'événements — uniquement si le module existe vraiment."""
    missing = module_status("analytics")
    if missing["status"] != "available":
        return missing
    try:
        from analytics import Analytics

        report = Analytics().report(days=1)
        return {
            "status": "ok",
            "source": "analytics",
            "total_events": report.get("total_events", 0),
        }
    except Exception as exc:  # pragma: no cover
        return {"status": "unavailable", "source": "analytics", "reason": type(exc).__name__}


def guardian_snapshot() -> dict:
    """Stats du guardian — uniquement si le module existe vraiment."""
    missing = module_status("guardian_v2")
    if missing["status"] != "available":
        return missing
    try:
        from guardian_v2 import Guardian

        stats = Guardian().stats()
        return {"status": "ok", "source": "guardian_v2", "stats": stats}
    except Exception as exc:  # pragma: no cover
        return {"status": "unavailable", "source": "guardian_v2", "reason": type(exc).__name__}


def display_value(snapshot: dict, key: str, unavailable: str = "غير متاح"):
    """Valeur prête à afficher : jamais `0` quand la source est absente."""
    if snapshot.get("status") == "ok" and key in snapshot:
        return snapshot[key]
    return unavailable


def guardian_display(snapshot: dict, unavailable: str = "غير متاح") -> dict:
    stats = snapshot.get("stats", {}) if snapshot.get("status") == "ok" else {}
    return {
        "blocked": stats.get("blocked", unavailable),
        "total_checks": stats.get("total_checks", unavailable),
    }
