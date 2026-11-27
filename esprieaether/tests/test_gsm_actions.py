"""J157 — TDD : chemin d'action GSM fermé jusqu'à SIM, destinataire et approbation.

Aucun test n'envoie de SMS ni n'appelle : on vérifie seulement que les portes
refusent. Le dossier ne contient aucun exécuteur.
"""

import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import gsm_actions  # noqa: E402


def status(ready_device=True, enabled=True):
    devices = [{
        "serial": "aaa",
        "model": "SM-G955U1",
        "sim_state": "READY" if ready_device else "ABSENT",
        "root": False,
        "termux": False,
    }]
    return {
        "ok": True,
        "status": "live_verified",
        "readOnly": True,
        "actionsEnabled": enabled,
        "online": 1,
        "devices": devices,
    }


def approval(decision="approved_once", decided_by="owner"):
    return {
        "id": "act-1234567890",
        "action": "gsm_send_sms",
        "status": decision,
        "decidedBy": decided_by,
    }


def request(**overrides):
    payload = {
        "action": "gsm_send_sms",
        "serial": "aaa",
        "to": "+212612345678",
        "message": "Test explicite",
    }
    payload.update(overrides)
    return payload


def prepare(payload, gsm=None, approved=None):
    return gsm_actions.prepare_action(payload, gsm or status(), approved or approval())


class GsmActionsTest(unittest.TestCase):
    def test_approval_manquante_bloque(self):
        result = gsm_actions.prepare_action(request(), status(), None)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "approval_missing")
        self.assertFalse(result["ready"])

    def test_approbation_refusee_ou_decision_inconnue_bloque(self):
        for decision in ("denied", "proposed", "executed", "anything"):
            with self.subTest(decision=decision):
                result = prepare(request(), approved=approval(decision))
                self.assertEqual(result["status"], "blocked")
                self.assertEqual(result["reason"], "approval_not_approved")
        result = prepare(request(), approved=approval(decided_by=""))
        self.assertEqual(result["reason"], "approval_no_actor")

    def test_type_d_action_inconnu_bloque(self):
        result = prepare(request(action="wipe_device"))
        self.assertEqual(result["reason"], "action_not_allowed")
        result = prepare(request(action="gsm_place_call", message=""))
        self.assertEqual(result["status"], "ready")

    def test_sim_non_ready_bloque(self):
        result = prepare(request(), status(ready_device=False))
        self.assertEqual(result["reason"], "sim_not_ready")

    def test_destinataire_manquant_ou_invalide_bloque(self):
        self.assertEqual(prepare(request(to=""))["reason"], "recipient_missing")
        for value in ("super", "123", "+212 612 34 56 78", "<script>"):
            with self.subTest(value=value):
                self.assertEqual(prepare(request(to=value))["reason"], "recipient_invalid")

    def test_message_manquant_ou_trop_long_bloque(self):
        self.assertEqual(prepare(request(message=""))["reason"], "message_missing")
        self.assertEqual(prepare(request(message="x" * 481))["reason"], "message_too_long")

    def test_interrupteur_explicite_du_proprietaire_bloque(self):
        result = prepare(request(), status(enabled=False))
        self.assertEqual(result["reason"], "actions_disabled")

    def test_toutes_les_portes_ok_ne_declenche_aucun_envoi(self):
        result = prepare(request())
        self.assertEqual(result["status"], "ready")
        self.assertTrue(result["ready"])
        self.assertFalse(result["sent"])
        self.assertNotIn("argv", result)
        self.assertNotIn("command", result)
        self.assertIn("local executor", result["next"])

    def test_aucun_executeur_dans_le_depot(self):
        package = SRC / "gsm_actions.py"
        source = package.read_text(encoding="utf-8")
        self.assertNotIn("subprocess", source)
        self.assertNotIn("touping", source)
        self.assertNotIn("input text", source)


if __name__ == "__main__":
    unittest.main()
