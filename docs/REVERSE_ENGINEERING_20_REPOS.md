# Reverse-engineering — 20 dépôts → ESPRIEATHER v2

Analyse des dépôts GitHub publics cités par le propriétaire. Aucun code n'a été copié :
seuls les **motifs d'architecture** ont été extraits, puis traduits dans le style local
(100 % offline, aucun token cloud, statuts véridiques avec TTL 7 jours).

## 1. Correspondance dépôt → idée → intégration

| Dépôt | Motif utile | Intégration ESPRIEATHER | Priorité |
|---|---|---|---|
| diegormirhan/voice-assistant | full-duplex barge-in, capture écran au moment de la parole, VAD live | durcir `voice_daemon.py` : RMS adaptatif + annulation réelle, preuve `barge_in` | P0 |
| PanPenek/JarvisAi-temporarly-depreciated | wake word + vision écran + 31 outils + HUD, mémoire SQLite/Chroma | compléter `atulya-wake`, ajouter mémoire locale au vault | P0 |
| FelipeMachado25/jarvis | agents LLM lisant un vault Obsidian en markdown, dégradation gracieuse | index BM25 local du vault + tool `recall_vault` | P0 |
| khoj-ai/khoj | second brain self-hosté, recherche sur docs, agents, interface Obsidian | même couche de recherche, sans service réseau | P0 |
| xark-argo/argo | gestionnaire de modèles one-click, RAG local, MCP | `model_manager.py` : reprise Range + SHA-256 + `llama-server` | P0 |
| ysunyang4/Nexus | ledger d'actions durable, contrôle MCP par l'utilisateur | durcir `state/action_audit.jsonl` + approval loopback | P1 |
| nanbingxyz/5ire | client MCP (tools/prompts), permissions par outil | confirmer `atulya-mcp` déjà `live_verified` via stdio | P1 |
| lee-b/kobold_assistant | invite explicitant que l'entrée vient de la STT | ajouter le préfixe Darija dans le prompt local | P2 |
| ServeurpersoCom/s2s.cpp | pipeline speech→speech dans un seul binaire GGML | inspiration pour réduire la latence du daemon | P2 |
| CWHISME/UiharuMind | GGUF/llama.cpp, OCR, connaissance, permission tier par outil | garder les outils locaux derrière un niveau de permission | P1 |
| DO0OG/Ari-VoiceCommand | wake word + STT/TTS + automatisation Windows | même pile : sherpa-onnx + faster-whisper + SAPI | P0 |
| uno-km/AMEVA-Window-Assistant | routage hybride OCR/VLM pour éviter l'OOM | ne charger le mmproj que quand la tâche est visuelle | P1 |
| novik133/jarvis | assistant KDE offline, HUD Iron Man | HUD local déjà existant (SSE, sans CDN) | P2 |
| melnikaite/voice-assistant | ASR streaming whisper.cpp + wake-word | déjà couvert par faster-whisper local | P2 |
| CoshkaX/Askria-Assistant | composition STT + LLM + TTS remplaçable | `jarvis_bridge.py` déjà compatible OpenAI-local | P2 |
| namrasamanta/anu-offline-assistant | alternative Kokoro TTS | garder Supertonic-3 + SAPI, pas de changement | P2 |
| alxpez/alts | STT locale hors ligne | faster-whisper déjà vérifié | P2 |
| ishangautam7/Talvio | dictée + exécution de tâches | `web_intents.py` déjà hooké | P2 |
| jaknak13-source/BuddyQ | faster-whisper sur Windows | modèle déjà téléchargé (tiny.en + base) | P2 |
| RayP11/Friday---Llama-Offline-AI-Assistant | LangChain + Ollama + Whisper + SAPI5 | équivalent local via `:31416`, sans LangChain cloud | P2 |

## 2. Ce qui est déjà couvert localement

- Cerveau local OpenAI-compatible `:31416` (`dolphin3`, timeout 120, retry 429).
- Voix : faster-whisper + Supertonic-3 + SAPI ; callback micro corrigé (`numpy.asarray().ravel()`).
- Réveil : 17 fichiers sherpa-onnx (`atulya-wake = implemented_unverified`).
- Vision : mmproj Qwen3.5-2B bf16 vérifié SHA ; inférence réelle en cours de préparation.
- MCP : `initialize` + `tools/list` + `tools/call` réels via stdio (`atulya-mcp = live_verified`).
- HUD : SSE locale, pas de CDN, pas de `onclick`, approval uniquement par `PUT` loopback.
- Vault Obsidian : `graph.html` local, 201 nœuds / 567 liens, 0 CDN.

## 3. Écarts réels à combler (P0)

1. **barge-in** : aucune preuve `barge_in` dans `voice_inbox.jsonl` → reste `implemented_unverified`.
2. **mémoire vault** : aucun index interrogeable → nouveau module BM25 local + capability dédiée.
3. **vision** : `vision_ready=true` ne suffit pas → preuve `vision_selfcheck.json` fraîche obligatoire.
4. **gestionnaire de modèles** : téléchargement manuel → module Range + retry + SHA intégré.

## 4. Règles conservées

- Aucun commit / push / upload.
- Aucun token, clé ou appel cloud.
- `live_verified` uniquement avec preuve datée (TTL 7 jours) ; sinon `implemented_unverified`,
  `not_available` ou `needs_user_data`.
- Tests d'abord (RED puis GREEN), puis mise à jour des checksums du manifest.
