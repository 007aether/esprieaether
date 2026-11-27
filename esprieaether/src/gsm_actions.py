#!/usr/bin/env python3
"""J157 — porte de préparation des actions GSM, fermée par défaut.

Ce module ne contient AUCUN exécuteur : il ne lance ni adb, ni SMS, ni appel,
et ne touche jamais au lanceur USB propriétaire. Il prépare une demande et
vérifie toutes les conditions posées par le propriétaire :

  1. décision ``approved_once`` explicite, avec un acteur identifié ;
  2. action dans une liste blanche ;
  3. interrupteur ``actionsEnabled`` mis à true par le propriétaire ;
  4. SIM ``READY`` sur l'appareil visé (preuve locale fraîche) ;
  5. destinataire explicite au format E.164 court ;
  6. texte explicite et borné pour un SMS.

Même quand tout est vert, le résultat reste ``sent=False`` : il faut encore
un exécuteur local approuvé, fourni séparément par le propriétaire.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

ALLOWED_ACTIONS = frozenset({"gsm_send_sms", "gsm_place_call"})
MAX_MESSAGE = 480
RECIPIENT_RE = re.compile(r"^\+?[0-9]{6,15}$")


def _blocked(reason: str, action: Any = None) -> Dict[str, Any]:
    return {
        "status": "blocked",
        "reason": reason,
        "ready": False,
        "sent": False,
        "action": action if isinstance(action, str) else None,
        "next": "Aucune commande n'a été envoyée ; corriger la porte bloquante.",
    }


def _recipient(request: Dict[str, Any]) -> str:
    for key in ("to", "recipient", "target"):
        value = request.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _message(request: Dict[str, Any]) -> str:
    for key in ("message", "text", "body"):
        value = request.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _ready_devices(gsm: Dict[str, Any]) -> list:
    devices = gsm.get("devices") if isinstance(gsm, dict) else None
    if not isinstance(devices, list):
        return []
    return [
        device for device in devices
        if isinstance(device, dict) and str(device.get("sim_state") or "").upper() == "READY"
    ]


def prepare_action(
    request: Dict[str, Any],
    gsm_status: Dict[str, Any],
    approval: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Valide sans exécuter. Retourne toujours un dict public, jamais une commande."""
    request = request if isinstance(request, dict) else {}
    gsm = gsm_status if isinstance(gsm_status, dict) else {}
    action = request.get("action")

    if not isinstance(approval, dict) or not approval:
        return _blocked("approval_missing", action)
    if str(approval.get("status") or "") != "approved_once":
        return _blocked("approval_not_approved", action)
    if not str(approval.get("decidedBy") or "").strip():
        return _blocked("approval_no_actor", action)
    if action not in ALLOWED_ACTIONS:
        return _blocked("action_not_allowed", action)
    if gsm.get("actionsEnabled") is not True:
        return _blocked("actions_disabled", action)

    ready = _ready_devices(gsm)
    if not ready:
        return _blocked("sim_not_ready", action)
    serial = str(request.get("serial") or "").strip()
    chosen = next((device for device in ready if device.get("serial") == serial), None)
    if chosen is None:
        if serial:
            return _blocked("sim_not_ready", action)
        chosen = ready[0]

    recipient = _recipient(request)
    if not recipient:
        return _blocked("recipient_missing", action)
    if not RECIPIENT_RE.fullmatch(recipient):
        return _blocked("recipient_invalid", action)

    message = _message(request)
    if action == "gsm_send_sms":
        if not message:
            return _blocked("message_missing", action)
        if len(message) > MAX_MESSAGE:
            return _blocked("message_too_long", action)

    return {
        "status": "ready",
        "reason": "",
        "ready": True,
        "sent": False,
        "action": action,
        "serial": chosen.get("serial") or "",
        "recipient": f"...{recipient[-4:]}",
        "next": (
            "Toutes les portes sont ouvertes, mais aucun local executor n'est branché : "
            "fournir un exécuteur local approuvé avant tout envoi réel."
        ),
    }


__all__ = ["ALLOWED_ACTIONS", "MAX_MESSAGE", "prepare_action"]
