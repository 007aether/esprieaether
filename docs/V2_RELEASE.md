# ESPRIEATHER v2.1.0 — version locale complète

## Nouveautés issues du reverse-engineering des 20 dépôts

- **Mémoire vault locale** (`esprieaether/src/vault_memory.py`) : index BM25 des
  notes Obsidian en markdown, sans embedding ni service externe. Requête réelle
  sur 212 notes → `atulya-vault-memory = live_verified`.
- **Outil `recall_vault`** dans Atulya : phrase déterministe
  « Search my Obsidian vault for … » → `Toolbox.call("recall_vault")`, avec la
  même politique d'approbation que les autres outils.
- **Gestionnaire de modèles résilient** (`esprieaether/src/model_manager.py`) :
  Range + `.part` + reprises + SHA-256 + remplacement atomique. Utilisé pour
  récupérer le runtime llama.cpp après une coupure réseau.
- **Preuve visuelle obligatoire** : `vision_ready=true` ne suffit plus.
  `atulya-vision` passe `live_verified` seulement avec une inférence récente
  (TTL 7 jours) dans `esprieaether/state/vision_selfcheck.json`.
- **Garde de sortie locale (J92)** : `egress_guard.py` refuse tout hôte de modèle
  non-loopback et tout bouton `open_website` vers un réseau privé. Preuve réelle
  dans `egress_selfcheck.json`, visible comme `local-egress-guard` dans le HUD.
- **Packaging v2.1** : `package.json` et `manifest.json` en `2.1.0`, ajout au
  manifest des modules locaux, des outils Atulya et des rapports d'analyse.

## Vérifications réelles (25/11/2026)

| Élément | Preuve | Statut |
|---|---|---|
| Inférence vision | image générée (cercle rouge) → llama.cpp + mmproj sur `:11438`, réponse « Red » en 16 s | `live_verified` |
| MCP local | `initialize` + `tools/list` + `tools/call` via stdio, `calculate("6*7") = 42` | `live_verified` |
| Mémoire vault | 212 notes indexées, requête « vision mmproj barge-in Atulya » | `live_verified` |
| Cerveau / voix / parole | `:8501/api/health` + `:31416` | `live_verified` |
| Modèle chat | 1 396 198 496 octets, SHA-256 `57a10858…a1d8` | intact |
| Barge-in | aucun événement `barge_in` réel enregistré | `implemented_unverified` |
| Éveil vocal | 17 modèles présents, pas d'essai micro réel | `implemented_unverified` |
| Approbation HUD | aucun `PUT` loopback réel dans `action_audit.jsonl` | `implemented_unverified` |
| Sources documentaires | aucun dossier `legal`/`fiscal`/`travail` fourni | `needs_user_data` |

## Tests

- Node : **1025 pass / 0 fail** (`tests\*.test.mjs`).
- Python unittest : **246 tests OK**.
- Atulya pytest : **495 passed, 3 skipped**, 12 subtests passés.
- Aucun commit, push, upload, token cloud ou clé externe.
