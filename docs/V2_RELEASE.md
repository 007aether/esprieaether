# ESPRIEATHER v2.1.4 — version locale complète

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
- **Approbation réelle (J76)** : `PUT` loopback vérifié sur `/api/jarvis/approvals/<id>`,
  transition `proposed→approved_once` tracée dans `action_audit.jsonl`.
- **Revue barge-in (J94)** : deux lignes `barge_in` désavouées parce que le micro
  est resté silencieux pendant la parole (0.0005 crête contre 0.18 de seuil) ;
  la capacité repasse `implemented_unverified`, sans réussite inventée.
- **Dépôt de sources (J93)** : `sources_intake.py` copie uniquement un fichier réel,
  calcule son SHA-256 et trace la provenance. Aucune source fournie pour l'instant.
- **Pont HUD ↔ Atulya (J95)** : le serveur `:3860` relaie `/atulya/*` et `/api/*`
  vers `:8501` sur la même origine, retire `x-frame-options`, remplace la CSP par
  une politique locale et supprime le script CDN Telegram. Le HUD ouvre Atulya
  dans un cadre local, sans `onclick` ni ressource externe.
- **Runtime gestuel local** : `tools/bootstrap.py` tolère l'absence de
  `LICENSE`/`NOTICE.md` dans le paquet npm 1.1.0 ; le modèle
  `gesture_recognizer.task` est installé avec SHA-256
  `97952348…0482` et les fichiers WASM sont vérifiés.
- **Statut gestuel corrigé** : `gesture_asset_status` n'exige plus les documents
  optionnels `LICENSE`/`NOTICE.md` absents du paquet npm ; `/api/status` affiche
  désormais `state=ready`, `Model ready · awaiting camera`.
- **Vérification navigateur réelle** : Chrome a ouvert `:3860/jarvis.html`, cliqué
  sur « abrir Atulya », chargé l'iframe `/atulya/` sur la même origine et confirmé
  les scripts locaux (aucun CDN). Seul `/api/push/subscribe` renvoie 403 (attendu,
  abonnement push non accordé).
- **Téléphone / APK** : l'appareil `iip` est appairé (`device_type=android`) mais
  `status=offline`, `seen=0`, un job `ping` reste en file d'attente : aucune preuve
  de polling ou de réception. L'APK n'est pas disponible dans le dépôt.
- **Darija par défaut** : `persona.build_system_prompt` impose la réponse en arabe
  marocain avec lettres arabes, quelle que soit la langue d'entrée ; le profil
  propriétaire est passé à `language=darija` et `darija` est mappé vers `ar` pour
  Whisper local. `ATULYA_FORCE_DARIJA=0` reste un désactivation explicite.
- **Outil `jarvis_status`** : Atulya lit JARVIS sur `http://127.0.0.1:3860` via
  des chemins fixes (`capabilities`, `system`, `attention`, `approvals`, `atulya`,
  `health`). Le modèle ne peut fournir aucune URL : pas de SSRF, pas d'approbation
  ou d'action déclenchée par cet outil. Disponible aussi en voix.
- **Autonomie owner activée** : `state/atulya/autonomy.json` contient
  `outside_messages=auto` à la demande explicite du propriétaire. Les outils
  confirmés par l'owner peuvent s'exécuter sans invite supplémentaire ; aucun
  SMS/appel n'a été envoyé lors de la configuration.
- **Packaging v2.1.4** : `package.json` et `manifest.json` en `2.1.4`, ajout au
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
