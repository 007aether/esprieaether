# ESPRIEATHER v2.1.6 — version locale complète

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
- **MCP sortant loopback** : Atulya accepte maintenant un serveur MCP local en
  `http://127.0.0.1` ou `http://[::1]` en plus de HTTPS distant ; `localhost`,
  `127.1`, les identifiants, query et fragment restent refusés. L'URL est
  revérifiée avant chaque test et chaque appel ; le test et l'octroi outil-par-outil
  restent obligatoires, et le protocole HTTPS distant inchangé.
- **Page de démarrage HUD** : `ATULYA_LANDING_URL=http://127.0.0.1:3860/jarvis.html`
  dans `START_ATULYA_TANTRA.cmd` et dans le superviseur `keep_alive.ps1`. `/`
  redirige vers le HUD, tandis que `/index.html`, `/assistant.js` et `/api/*`
  restent servis localement par Atulya. Le pont `:3860` traduit `/atulya/` en
  `/index.html` pour éviter une boucle de redirection dans l'iframe.
- **Autonomie owner étendue** : `autonomy.json` contient aussi
  `repairs=apply_if_tests_pass`. Seules les petites réparations listées
  (music, TTS, device companion, skills) peuvent être appliquées sans click,
  avec rollback si les tests échouent ; WebUI, brain, auth et setup exigent
  toujours une approbation. Aucun SMS, appel ou action d'appareil envoyé.
- **Packaging v2.1.6** : `package.json` et `manifest.json` en `2.1.6`,
  **811 fichiers** inventoriés, ajout au manifest des modules locaux, des quatre
  agents, du script de tournée, des outils Atulya et des rapports d'analyse.
- **Répondeur unique (J97/J98)** : le superviseur 24/7 garde Atulya et le HUD en
  vie, et désactive le daemon vocal JARVIS hérité par défaut (`voice=atulya-only`).
  `ESPRIE_LEGACY_VOICE=1` le réactive explicitement ; la persona Atulya ne dit plus
  « in the style of Jarvis ». Aucun SMS, appel ou action d'appareil déclenché.
- **Darija renforcée (J99)** : la bulle d'accueil est `صباح الخير.` /
  `مساء الخير.` / `مرحبا بعودتك.` ; la voix du navigateur détecte l'écriture arabe
  et choisit `ar-MA` au lieu de `en-IN`. Le routeur `:31416` n'injecte plus la
  consigne darija qu'une fois, même si le prompt contient déjà « دارجة ».
- **Prompts plus courts** : persona 1704 → 1020 caractères, profil 885 → 493
  (total 2591 → 1515), une seule règle d'honnêteté et une seule règle de longueur.
- **URL centralisées** : `atulya/urls.py` valide aussi bien MCP que
  `ATULYA_LANDING_URL` et `public_origin` ; ports invalides et `?`/`#` vides refusés.
- **Tests plus rapides** : hachage partagé du paquet source, `noLinks` à visite
  unique et entries ZIP compressées mises en cache. `install.test.mjs` et
  `update.test.mjs` passent de 331 s à 159 s sans retirer aucun test.
- **Cache du pont HUD** : les fichiers statiques sont lus une seule fois tant que
  taille, mtime et ctime ne changent pas ; `no-store`, 403/404 et en-têtes de
  sécurité inchangés.
- **Node local et MCP stdio** : `maintenance.py` résout Node depuis
  `ATULYA_NODE_BIN`, puis le `PATH`, puis `.tools\node-v26.13.1` embarqué. Le test
  MCP transmet explicitement `PYTHONPATH` au sous-processus, car le SDK MCP ne
  l'hérite pas par défaut.
- **Origine du pont (J100)** : les méthodes `POST`/`PUT`/`PATCH`/`DELETE` relayées
  vers Atulya portent désormais `Origin: http://127.0.0.1:8501` et
  `Sec-Fetch-Site: same-origin`. Sans cela l'iframe servie sur `:3860` recevait
  un `403` sur `/api/chat`.
- **Interface entièrement en darija (J101/J104)** : les libellés du HUD Atulya,
  les phases, les messages d'erreur de flux, les panneaux (réglages, appareils,
  outils, musique, rappels, connexions) et le briefing du matin sont traduits
  en arabe marocain. Les pages de supervision `jarvis.html` et `system.html`
  sont aussi entièrement en darija, avec un dictionnaire `tr()` pour les statuts
  dynamiques (`no_data_source`, `live_verified`, `proposed`, etc.). Les
  identifiants DOM et les noms de variables JS ne changent pas ; les valeurs
  dynamiques passent par `darija()` ou `tr()` avant affichage.
- **Page autonome + fenêtre flottante (J102)** : `/atulya/` sert la page complète
  en local, et le HUD propose Atulya dans une fenêtre déplaçable, fermable par
  `Escape`, sans `onclick`, sans `POST` littéral et sans CDN.
- **Preuve d'éveil vocal (J103)** : `atulya-wake --evidence` écrit
  `wake_selfcheck.json` en local avec `ok`, `hits`, `peak`, `device` et `ts`.
  `api/server.mjs` n'accorde `live_verified` que sur un dossier frais (TTL 7 jours)
  avec `ok=true` et `hits>0` ; sinon la capacité reste `implemented_unverified`.
- **Acquittements et erreurs en darija (J105)** : les phrases instantanées
  (`Checking the systems.` → `كنفحص الأنظمة.`, `One moment.` → `لحظة من فضلك.`)
  et tous les messages `BrainError` / `ProviderError` sont en arabe marocain.
  Les mots-clés darija (`الطقس`, `حالة النظام`, …) déclenchent aussi l'acquittement.
- **Journal de panne sans secret (J106)** : `brain_errors.jsonl` n'enregistre
  qu'une liste blanche de champs (`type`, cause, étape, fournisseur, modèle,
  durée, code HTTP, nouvelle tentative). Le texte libre est filtré et plafonné ;
  aucun prompt, en-tête, jeton ni mot de passe n'est persisté. Le serveur trace
  désormais la cause avant d'envoyer le message vocal générique.
- **Reprise de flux et garde-fous (J107/J109)** : une seule nouvelle tentative
  quand le flux tombe avant le premier mot ; sinon une phrase darija explicite
  termine la réponse et le `done` SSE reste émis. Les résultats d'outils sont
  plafonnés, les erreurs d'outils sont rendues au modèle pour correction, et
  l'historique long est résumé sans jamais transformer l'historique en prompt
  système.
- **Superviseur résilient (J108)** : plus de `-ArgumentList` vide ; chaque
  démarrage est isolé et journalisé (`START_FAILED`) sans arrêter la tournée.
  FreeLLMAPI reste hors démarrage automatique tant que le propriétaire ne le
  demande pas explicitement.
- **تنبيهات اللوحة (J110)** : `guard_failed/python` كان جاي من اختبار قديم كيتوقع صيغة فرنسية فـ `persona.py`؛ تصلّح باش يتحقق من الدارجة بحروف عربية. `guard_failed/endpoints` وخدمات `down` كانو كيعتابرو `dsh_bridge` و`llm_gateway` أخطاء، وهم خدمات ببدء يدوي/مستقل؛ ولا كيتسجلو كـ `manual_services_down` معلومة غير خطأ. العدّاد التراكمي `failed_runs` و`timed_out_runs` ولا معلومة، والإنذار كيبقى غير للفشل القريب فـ `run_needs_attention`. التعديلات كتطلب إعادة تحميل الحارس والمشغل باش تبان فاللوحة.
- **حصة FreeLLMAPI وCLAUDE CODE (J111)** : المرحّل المحلي `/freellm/*` كيقرأ المفتاح وقت التشغيل من `state/freellmapi.key` (ما كيكتبو فأي ملف)، كيمنع التليمتري والطلبات غير الضرورية، وكيعطي Claude Code غير الحقول المدعومة (`stream=false` بلا `thinking` ولا `context_management`) باش ما يعلّقش. كل طلب `/v1/messages` ولا `/v1/chat/completions` كيتسجّل فـ `state/model_share.jsonl` غير بـ `ts` و`consumer` و`model` و`ok`، بلا prompt ولا توكن. السينتيل كيعرض `FRELLMAPI` و`CLAUDE CODE` مع نسبة الحصة فـ SSE وHUD. مشغّل `start_claude_code_local.ps1` كيقرأ المفتاح فالجلسة غير.
- **بطاقات الخدمات (J112)** : `/api/health` ولا كيرجّع `jarvis_backend` و`ollama_reason` بقيمة `active` (بدل `local-brain` و`service local actif` اللي كانو كيبانو حمر فالواجهة). اسم المزوّد تنتقل لـ `jarvis_backend_provider`، والرسالة الاحتياطية ولا بالدارجة بحروف عربية.
- **Traduction des documents de test** : les assertions de `briefing_settings`
  suivent le nouveau libellé darija du briefing matinal.

## Quatre agents locaux et tournée quotidienne (J117–J126)

- **Veille GitHub en lecture seule** (`esprieaether/src/github_scout.py`) : une
  seule sortie HTTPS, l'hôte exact `api.github.com`, sans jeton ni secret lu ou
  écrit. 1000 dépôts réels en 10 pages × 4 requêtes, espacement et reprises sur
  403/429, échantillon et sujets sanitisés dans `github_scout_report.json`. TDD
  RED 1 → GREEN 7/7, plus 3 contrôles CLI/limite de débit (J124/J126).
- **Docteur local réparateur** (`esprieaether/src/doctor_agent.py`) : détecte
  dans `state/` et dans `propose_fixes`, propose des patchs littéraux uniques,
  applique via `tmp + os.replace` uniquement dans `state/` ou les 3 fichiers de
  la liste blanche, et avertit Atulya dans la même passe
  (`doctor_notices.jsonl`). Aucun `pkill`, redémarrage, commit, push ni réseau.
  Exécution réelle : `detected=2`, `fixed=2`, `needsRestart=false`. Le défaut
  réel `item["severity"]` de `self_improve.py` a été corrigé en
  `item.get("severity") or "routine"` et ajouté à chaque sortie. TDD RED → GREEN
  9/9 + 4 contrôles d'auto-réparation (J123).
- **Ingénierie inverse locale** (`esprieaether/src/rea_agent.py`) : 7960 fichiers
  analysés en local, blueprint dans `docs/rea/`, wrappers compatibles
  (`doctor`, `investigate`, `status_report`, `inventory`) sans subprocess ni
  réseau. TDD RED → GREEN 6/6 + 4/4 compatibilité.
- **Apprentissage enrichi** (`esprieaether/src/learning_agent.py`) : lit aussi
  `github_scout_report.json` comme source locale, passe par `policy_gate`
  avec `internet=false`, masque les secrets et ne propose aucune exécution.
  Passe réelle : 96 leçons, 6 sources ; les comptages réels du rapport
  (`topics`/`languages` en dict) sont aussi retenus avec leur top 3 (J122/J127).
- **Tournée quotidienne** (`esprieaether/src/daily_orchestrator.py`) : ordre
  `github-scout` → `doctor` → `rea` → `learning`, date-gate 24 h, chaque agent
  dans son propre `try`, écriture atomique de `daily_orchestrator_report.json`.
  Aucun réseau ajouté, aucun commit/push/redémarrage. TDD RED → GREEN 6/6 +
  contrôle CLI cp1252 (J125).
- **Registre et HUD** : `AGENTS`, `AGENT_DUTIES`, `AGENT_REPORTS` et
  `/agents/{id}/run` (lecture du seul selfcheck public) dans `espria_system.py` ;
  trois capacités `github-scout`, `doctor`, `rea` avec preuve fraîche TTL 7 jours
  et dégradation honnête dans `api/server.mjs`. TDD RED → GREEN 3/3 + 3/3.
- **Ordonnanceur actif** : tâche locale `SUNNAVOK_DAILY_AGENTS` enregistrée à
  05:00 chaque jour, qui appelle `esprieaether/scripts/daily_agents.ps1 -Once`
  sous mutex, sans Telegram ni push ni action d'appareil.

## Vérifications réelles (25/11/2026)

| Élément | Preuve | Statut |
|---|---|---|
| Inférence vision | image générée (cercle rouge) → llama.cpp + mmproj sur `:11438`, réponse « Red » en 16 s | `live_verified` |
| MCP local | `initialize` + `tools/list` + `tools/call` via stdio, `calculate("6*7") = 42` | `live_verified` |
| Mémoire vault | 212 notes indexées, requête « vision mmproj barge-in Atulya » | `live_verified` |
| Cerveau / voix / parole | `:8501/api/health` + `:31416` | `live_verified` |
| Accueil darija | `GET :3860/atulya/assistant.js` → 200 ; `مساء الخير.` présent, `Good evening.` absent | `live_verified` |
| Répondeur unique | superviseur 24/7 en `voice=atulya-only`, daemon JARVIS hérité arrêté | `live_verified` |
| Modèle chat | 1 396 198 496 octets, SHA-256 `57a10858…a1d8` | intact |
| Barge-in | `voice_inbox.jsonl` : `reason=barge_in` à `2026-11-26T02:55:19Z` (voix réelle captée par le micro du navigateur, WAV SAPI local lu dans le navigateur puis interrompu) | `live_verified` |
| Éveil vocal | `wake_selfcheck.json` `ok=true`, `hits=1`, score `0.7876` à `2.4 s`, `peak=0.266724` sur 11,9 s de micro navigateur (`getUserMedia`, 16 kHz) lu par `hey_jarvis_v0.1.onnx` ; STT local : « Hi Jarvis. » Aucun envoi réseau. | `live_verified` |
| Interface darija | HUD, panneaux, musique, réglages et briefing sans libellés anglais visibles | `live_verified` |
| Page autonome / fenêtre flottante | `/atulya/` local + fenêtre déplaçable, sans CDN ni `onclick` | `live_verified` |
| Approbation HUD | aucun `PUT` loopback réel dans `action_audit.jsonl` | `implemented_unverified` |
| Sources documentaires | 6 PDF réels `legal`/`fiscal`/`travail` ingérés depuis GitHub (lecture seule) | `live_verified` |
| MCP externe | aucun endpoint HTTPS externe fiable ni octroi outil-par-outil fourni | `needs_user_data` |
| Veille GitHub (26/11) | `github_scout_report.json` `ok=true`, `scanned=1000`, 4 requêtes, `checked_at=2026-11-26T04:24:44Z`, lecture seule de `api.github.com`, aucun jeton | `live_verified` |
| Docteur local (26/11) | `doctor_selfcheck.json` `ok=true`, `status=live_verified`, `detected=2`, `fixed=2`, `codeFixed=0` (correctif déjà appliqué), `needsRestart=false`, 2 avis locaux dans `doctor_notices.jsonl` | `live_verified` |
| Ingénierie inverse (26/11) | `rea_selfcheck.json` `ok=true`, `files=7960`, blueprint `docs/rea/esprieaether/blueprint.md`, wrappers sans subprocess | `live_verified` |
| Apprentissage (26/11) | `learning_selfcheck.json` `learnedCount=96`, 6 sources dont `github_scout_report.json`, `engine=local_only` ; le top 3 des sujets/langages est appris avec ses comptages (`topic=ai:338`, `language=Python:463`, …) | `live_verified` |
| Tournée quotidienne (26/11) | `daily_orchestrator_report.json` `status=live_verified`, 4 agents, date-gate 24 h, tâche `SUNNAVOK_DAILY_AGENTS` à 05:00 et passe `-Once` journalisée dans `daily_agents.log` | `live_verified` |
| HUD des nouveaux agents | `:5100` بعد إعادة تحميل بموافقة كيرجّع **15 قدرة**: `github-scout`، `doctor`، `rea`، `gsm-fleet`، `gsm-model-trial` مضافين للـ 10 القديمة بـ evidence وTTL 7 أيام | `live_verified` |

## Tests

- Node : **1091 pass / 0 fail** sur les fichiers `tests\*.test.mjs` (dont J114,
  J115, les 3 contrôles `jarvis_new_agents.test.mjs`, les 5 de `gsm_capability`,
  les 3 de `health_provider`, les 4 du bot autonome J131, le contrôle J132 du
  wrapper `npm test`, le contrôle J133 de fermeture keep-alive et les 2 gardes
  J134/J135 des délais sous charge, le garde J136 du scan de secrets et les 3
  gardes J137/J139 de réactivité d’Atulya), dont le test
  d'origine du pont `J100`, le contrôle darija des pages `jarvis.html` /
  `system.html`, le délai `120000` du relais, la fermeture clavier de la fenêtre
  flottante, les contrôles J106/J108, le contrôle J110 des services en démarrage
  manuel, les 2 contrôles J111 du relais et du lanceur Claude Code local, et les
  contrôles d'installation du manifeste à 817 fichiers.
- Node ciblé (pont, darija, install/update) : **157/157** (155 + les 2 contrôles J106/J108).
- Python unittest : **324 tests OK / 0 fail** à la deuxième passe (la première
  a eu un `test_voice_daemon` transitoire, vert seul et vert à la reprise), dont
  259 tests de base (J110 à J114), 9 contrôles du docteur, 4 contrôles
  d'auto-réparation (J123), 7 contrôles de la veille GitHub (dont CLI cp1252 et
  reprise 403/429), 6 contrôles de l'ordonnanceur, 6 contrôles `rea` + 4
  compatibilité, 5 contrôles du registre des agents, 14 contrôles du pont GSM
  (J129/J130) et 3 contrôles d'apprentissage depuis la veille (J122/J127, listes
  et comptages). Aucun test supprimé ni affaibli.
- Atulya pytest : **566 passed, 3 skipped**, 16 subtests passés (0 fail),
  dont les 7 contrôles darija (J105) et les 6 nouveaux contrôles J106/J109
  (journal sans secret, reprise de flux, erreurs d'outils, plafond de résultat,
  compression de l'historique). Passe rejouée dans le `.venv` local avec
  `webauthn` installé et le Node local `.tools\node-v26.13.1` sur `PATH` ;
  le premier essai sans ce Node avait donné un faux `test_web_ui_still_needs_approval`
  (« Node is unavailable »), corrigé par le `PATH` sans toucher au code. Le premier
  essai avec le `.venv` de `esprieaether` avait donné `No module named pytest` :
  la passe valide utilise bien `GITHUB_IMPORT\Atulya-Tantra\.venv`.
- Bot autonome local (J131) : `scripts\autonomous_checks.mjs` enchaîne Node,
  unittest, pytest Atulya, scan ADB des 20 S8 en lecture seule, sonde des
  endpoints et régénération du manifeste, puis écrit
  `esprieaether\state\autonomous_report.json` avec les seuls statuts autorisés.
  TDD RED `ERR_MODULE_NOT_FOUND` puis GREEN 4/4. Aucun SMS, appel, root, APK ni
  écriture appareil. `--autonomous` ne commit/pousse et ne recharge `:5100`/`:5000`
  que si tout est vert ; les quatre permissions ont été données explicitement.
  Tâche planifiée `aut_2170a49bf001xRhAu3IvEM95mr` à 06:00 chaque matin
  (`Africa/Casablanca`).
- Correctifs J132/J133 : `scripts\run-checks.mjs` cible uniquement `tests/` au lieu
  de balayer les sauvegardes `BACKUP_*` (faux `browser.mjs` / fixtures bloqués),
  et le serveur de test JARVIS libère ses connexions keep-alive avant `close()`.
  Deux tests de garde TDD (RED puis GREEN), manifeste régénéré après chaque
  modification de source.
- Correctifs J134/J135 : le client MCP stdio d'Atulya passe de 5 à 30 secondes et
  le CLI de référence de 15 à 120 secondes ; sous charge ces délais donnaient des
  `MCPError: Request 'initialize' timed out` et `status=null !== 0` sans défaut
  de logique. Deux gardes TDD (RED puis GREEN) et test ciblé vert à chaque fois.
- Garde J136 : le scan de secrets du bot ignore ses propres littéraux de test
  (`const SECRET`, `api_key: abc123`, `token=abc`) sans ignorer les vraies clés.
  TDD RED puis GREEN 5/5, ce qui débloque le commit/push automatique.
- Réactivité Atulya (J137/J139) : `/api/health` et `/api/auth/status` ne passent
  plus par la base SQLite d’interdiction d’IP ; les sondes WebUI passent de 3 à
  10 secondes ; surtout `model_assets_ready()` met en cache les empreintes
  SHA-256 des 7 fichiers du modèle TTS au lieu de les recalculer à chaque appel.
  Mesure locale après redémarrage : `/api/health` de **600–6700 ms** avant à
  **11–156 ms** après, `/api/auth/status` de **~1200 ms** à **~20 ms**.
  Trois gardes TDD (RED puis GREEN), `tests/voice/test_tts.py` 3/3 vert et
  redémarrage de `:8501` avec le même environnement local.
- GSM local et Atulya (J140) : le port ADB local est fixé à 5038 (surchargeable
  par `ESPRIE_GSM_ADB_PORT`) et transmis au sous-processus sans modifier les
  arguments en lecture seule ; `gsm_status.json` publie `adbPort` et
  `adbStates`. Côté Atulya, `/api/auth/status` lit un seul snapshot SQLite au
  lieu de six connexions, le cache KV vocal ne cible que le runtime llama local
  (11435) et jamais le gateway `31416`, `/api/status` ne collecte qu'une fois
  les métriques hôte, et `/api/chat` ne vérifie `is_admin` qu'une fois.
  Douze gardes TDD (RED puis GREEN), Python **327 OK** et Atulya
  **575 passed / 3 skipped**.
- Wakil / rapport local (J141) : `conversation_report_agent.py` lit une liste
  blanche de fichiers `state`, masque les secrets, écrit un rapport honnête dans
  la conversation `wakil_reports` de l'archive Atulya (rôle `assistant`) et
  dépose les suggestions dans `action_requests.json` au état `proposed`.
  Rien n'est exécuté automatiquement : la décision se fait dans le HUD.
  Le rapport est limité à une fois par 24 h et le cinquième agent est branché
  sur `daily_orchestrator.py`. Cinq gardes TDD (RED puis GREEN) plus les cinq
  gardes de l'ordonnanceur mis à jour ; un passage réel a écrit 1 message et
  4 propositions `proposed` visibles sur `/api/jarvis/approvals`.
- Aucun upload, token cloud ou clé externe.

## شنو ناقص (MADA YANKOSONA)

> كل اللي كيتطلب بيانات ديالك أو جهاز حقيقي، ما تدارش بلا طلب صريح منك.

| العنصر | الحالة | شنو كيتطلب باش يتحقق |
|---|---|---|
| `external_mcp` | `needs_user_data` | عنوان HTTPS خارجي حقيقي + منح كل أداة علىحدة بعد `Test & discover tools`. |
| `documentary-sources` | `live_verified` | 6 ملفات حقيقية من GitHub (قراءة فقط) تّدخلو بـ `sources_intake.py`؛ `backlog_scout_report.json` كيقول `missing_sources=[]` و`checked_at=2026-11-26T03:48:47Z`. `legal/legal_rapport.pdf`، `fiscal/{CGI-2025,LOI de finances 2026,PCM}.pdf`، `travail/{Code du travail,Guide}.pdf`؛ الشّا ديال كل واحد محفوظ فـ `sources_intake.jsonl`. |
| APK / جهاز `iip` | `needs_user_data` | APK أو ربط جهاز أندرويد؛ الجهاز دابا `offline`، `seen=0`، وطلب `ping` مصفوف بلا إيصال. ما تدار أي فعل جهاز. |
| `barge-in` | `live_verified` | سطر `barge_in` فـ `voice_inbox.jsonl` بـ `2026-11-26T02:55:19Z`؛ صوتك (عبر ميكرو المتصفح، RMS `0.0468`) قطّع WAV محلي بـ SAPI كان كيتشغّل فالمتصفح. |
| سجل توقف الجواب | `implemented_unverified` | أول توقف حقيقي كيكتب سطر فـ `brain_errors.jsonl`؛ الاختبارات غطّات الحالات، ولكن ما وقعش توقف جديد فالسيرفر الحي بعد TDD. |
| `atulya-wake` | `live_verified` | `wake_selfcheck.json` : `ok=true`, `hits=1`, score `0.7876` فـ `2.4 s`، `peak=0.266724`؛ كلمة «Hey Jarvis» قلتيها و الميكرو ديال المتصفح سجّلها محلياً بلا شبكة. |
| موافقة HUD | `live_verified` | `action_audit.jsonl` فيه `act-9ec94b52eb`: `proposed->approved_once` فـ `2026-11-25T09:03:37.179Z` من `hud`. |
| تنبيهات `guard_failed/python` و`guard_failed/endpoints` | `live_verified` | من بعد إعادة التحميل بموافقة صريحة، `quality_guard_report.json` ولا `checks.endpoints=true` و`guard_failed/python` و`guard_failed/endpoints` و`SYS_01/SYS_02` اختفاو. |
| عدّاد `failed_runs` / `timed_out_runs` التراكمي | `live_verified` | ولا معلومة فالـ dashboard؛ الإنذار كيبقى للفشل القريب غير (تحقّق بعد إعادة تحميل `api/server.mjs`). |
| self-heal ديال الـ supervisor | `live_verified` | `keep_alive.ps1` تحمّل بموافقة صريحة؛ `ReleaseMutex` وقت الإقلاع ما منعش المشرف من الخدمة. |
| `/api/chat` غير-streaming | تحسّن بعد موافقة | الـ `timeout` ولا `120000` فـ `serve_g0dm0d3.mjs`، الـ UI كيستعمل streaming. |
| محادثة كاملة بمصادقة (J115) | `live_verified` | بعد إيماءة passkey ديالك فـ `http://localhost:8501/index.html`، `/api/auth/status` ولا كيرجّع `authenticated=true`, `user=Admin`, `is_admin=true`. جرّينا جولين بـ `stream=true` فـ `/api/chat` على `conversation_id=mada_yankosona_20261126`، وكل جول رجّع `200` مع `done=true` و`provider=Configured model provider` و`model=dolphin3` (محلي، بلا شبكة). `chat_auth_selfcheck.json` فيه `method=passkey`, `turns=2`, `checkedAt=2026-11-26T03:49:59Z`، بلا cookie ولا token مكتوبين. القدرة `chat-auth` و`/api/jarvis/chat-auth` تّختارو بـ TDD (RED 3/3 ثم GREEN 3/3)؛ أُعيد تحميل `:5100` بموافقة صريحة وبانو فالـ HUD الحي. |
| حزمة unittest محلية (root) | تحقّق بعد J112 | **253 passed / 0 fail**؛ كان فيها اختبار واحد كيتوقع صيغة فرنسية قديمة فـ `persona.py`، تصلّح باش يقرأ الدارجة بحروف عربية. Atulya pytest ولا **566 passed / 3 skipped** بـ `.venv` محلي و Node على `PATH`. |
| حصة FreeLLMAPI / Claude Code (J111) | `live_verified` | بعد إعادة تحميل mock والتجميع، `/health` وSSE ديال `:8766` كيبانو فيهم `FRELLMAPI` و`CLAUDE CODE` مع `shares`؛ `/freellm/health` و`/freellm/stats` خدمو على `:3860`؛ `start_claude_code_local.ps1` رجّع `OK` بموديل `claude-sonnet-4-5` بلا اتصال خارجي. |
| بطاقات الخدمات (J112) | `live_verified` | `/api/health` الحي ولا كيرجّع `jarvis=active`، `jarvis_backend=active`، `jarvis_backend_provider=local-brain`، `ollama_reason=active` و`web=active`. |
| وكيل التعلّم المحلي (J114) | `live_verified` فالـ selfcheck | `learning_selfcheck.json` فيه `engine=local_only`، `learnedCount=96`، 6 مصادر محلية (`run_ledger.json`, `action_audit.jsonl`, `voice_inbox.jsonl`, `action_requests.json`, `sources_intake.jsonl`, `vault_memory`). التعلّم كيقرأ غير، كيمرّر عبر `policy_gate` بـ `internet=false`، كيخفي الأسرار قبل التخزين، وما كيقترح أي تنفيذ. `/api/jarvis/learning` والقدرة `local-learning` تّختارو بـ TDD (RED 3/3 ثم GREEN 3/3)؛ أُعيد تحميل `:5100` بموافقة صريحة وبانو فالـ HUD الحي. |
| الوكلاء الجدد (J117–J126) | `live_verified` فالـ selfchecks | `github_scout_report.json` (1000 مستودع، قراءة فقط)، `doctor_selfcheck.json` (2 إصلاحات، بلا إعادة تشغيل)، `rea_selfcheck.json` (7960 ملف)، `learning_selfcheck.json` (73 درس، 6 مصادر)، و`daily_orchestrator_report.json` (4 agents، date-gate 24 h). تّسجلو فـ `AGENTS`/`AGENT_DUTIES` وفـ `/agents/{id}/run` قراءة فقط. |
| الجدولة اليومية | `live_verified` محلياً | المهمة `SUNNAVOK_DAILY_AGENTS` كتدير passe واحدة كل نهار على 05:00 عبر `daily_agents.ps1 -Once` تحت mutex؛ كيمرّر على الطبيب والهندسة العكسية والتعلّم، بلا Telegram ولا push ولا شبكة غير GitHub القراءة. ما تدار أي فعل جهاز. |
| تنظيف سر قديم (26/11) | `live_verified` | كلمة مرور كانت مكتوبة فـ `aether-v7/src/esprie/tools.py` و`browser_automation.py` تّشالت من ملفات الشغل؛ ولاّت تُقرأ وقت التشغيل من `ESPRIE_EMAIL` / `ESPRIE_PASSWORD`. ما كُتب أي سر فأي ملف جديد. السر باقي فـ git history القديم، ومحوه كيتطلب rewrite تاريخي بموافقة منفصلة. |
| HUD بـ 15 قدرة | `live_verified` بعد إعادة تحميل بموافقة | `api/server.mjs` و`espria_system.py` فيهما `github-scout` و`doctor` و`rea` و`gsm-fleet` و`gsm-model-trial` بـ evidence وTTL 7 أيام؛ `:5100` ولا كيرجّع 15 قدرة، منهم `gsm-fleet` بـ `online=20` و`probeStatus=live_verified` و`gsm-model-trial` بـ `needs_user_data`. |
| فلوت GSM المحلي (J129/J130) | `live_verified` فالـ state | `gsm_status.json` : `ok=true`، `online=20`، `errors=[]`، `readOnly=true`، `worker.mode=thin_endpoint`، `worker.ready=20`، `checkedAt=2026-11-26T07:50:04Z`. 20 جهاز Samsung S8/S8+ عبر `adb.exe` المحلي، COM43–COM60. الجرد: Android **9** (SDK 28)، `arm64-v8a`، `root_count=0`، `termux_count=0`، RAM فارغة **175–517 MB**، تخزين **50 GB**. غير `sms` ولا `call` ولا `input text`؛ `SIM=ABSENT` على أغلبية الأجهزة. |
| عُقد GSM الخفيفة (J130) | `live_verified` فالـ state | `gsm_workers.json` : `ok=true`، `online=20`، `succeeded=60`، `tasks=status,battery,props`، `errors=[]`، `readOnly=true`، `gateway=http://127.0.0.1:31416`، `checkedAt=2026-11-26T07:50:25Z`. ولا APK، ولا root، ولا تثبيت، ولا مكالمة/SMS. الأفكار من PhoneBorg (Apache-2.0) و`llama-cpp-android-node` استُعملت للفكرة غير كُنسخ منها شيء. |
| تجربة موديل صغير على جهاز واحد (J130) | `needs_user_data` | `gsm_model_trial.json` : `ready=false`، `reason=binaire llama.cpp arm64 ELF local absent; GGUF local <= 600 Mo absent`، `checkedAt=2026-11-26T07:50:16Z`. أصغر GGUF محلي كاين **1331 MB** (Qwen 2B Q4)، كبير على RAM المتاحة؛ ما كاين لا NDK ولا بinaire arm64. ما تدار أي download، والخطوة كتطلب توفير الملفات محلياً ثم benchmark على جهاز واحد. |
| بطاقة `jarvis_backend_provider` (J129) | `live_verified` | `/health` كيرجّع `local-brain` كاسم مزوّد؛ الواجهة ولا كتعرضو بـ ℹ️ معلومة محايدة وما كتحسبوش فعدّاد الخدمات (6/6 بدل 6/7). ما بقاتش كبان 🔴. |
| البوت المحلي المستقل (J131) | `live_verified` فالجولة النهائية | `scripts/autonomous_checks.mjs` كيجرب Node وPython وAtulya و20 GSM (قراءة فقط) وكيكتب `autonomous_report.json` بـ statuses مسموحين. `(RED 4/4 → GREEN 4/4)`. scheduled `aut_2170a49bf001xRhAu3IvEM95mr` كل نهار 06:00 بتوقيت الدار البيضاء. كيعمل commit/push وإعادة تحميل غير إلا كانت الجولة كلها خضراء، وبموافقة صريحة منك. الحالة الحية كتتحقق فالجولة النهائية. |
| `npm test` ما كيباليش BACKUP (J132) | `implemented_unverified` فالملفات | `scripts/run-checks.mjs` ولا كيعطي `tests/` صراحة؛ قبل كان كيكتشف 2060 اختبار من `BACKUP_20261121` وكيعلق على fixtures ديال stdin. اختبار حارس TDD RED ثم GREEN. |
| إغلاق خادم اختبار JARVIS (J133) | `implemented_unverified` فالملفات | `tests/jarvis_atulya.test.mjs` كيستعمل `closeAllConnections()` و`connection: close`؛ قبل كان kipqa msawwar فـ `server.close` b keep-alive. اختبار حارس TDD RED ثم GREEN. |
| المدد تحت الضغط (J134/J135) | `live_verified` بعد اختبارات موجهة | MCP stdio ولّى `read_timeout_seconds=30` وCLI المرجع `timeout: 120000`؛ قبل كانو 5 و15 ثانية وكيطيحو فـ `initialize timed out` / `status=null`. حارسان TDD RED ثم GREEN، والاختبار الموجه رجع أخضر. |
| فحص الأسرار فالبوت (J136) | `live_verified` بعد اختبار موجه | البوت ولا كيميّز بين literals ديال الاختبار والسر الحقيقي؛ قبل كان كيمنع commit بـ 3 أسطر falses. حارس TDD RED ثم GREEN 5/5. |
| استجابة Atulya (J137/J139) | `live_verified` بعد قياس حي | `/api/health` و`/api/auth/status` ولاو كيتجاوزوا SQLite فالسondes، وSHA-256 ديال 7 ملفات TTS ولا كيتحسب غير مرة. القياس: health من 600–6700ms لـ 11–156ms، auth/status من ~1200ms لـ ~20ms. سondes الواجهة من 3s لـ 10s. 3 حوارس TDD RED ثم GREEN، و`:8501` أُعيد تحميله بنفس البيئة المحلية. |
| GSM وAtulya (J140) | `live_verified` بعد اختبارات وسموك حي | منفذ ADB تثبّت على 5038 و كيتورّث للـ subprocess بلا ما نبدّل argv القراءة، و`gsm_status.json` ولا كيعرض `adbPort` و`adbStates` (20/0/0). Atulya ولا كيقرا `auth/status` بـ snapshot واحد، وprefix الصوت كيبقى غير للـ runtime المحلي 11435، و`/api/status` كياخد snapshot واحد، و`is_admin` ولا مرة واحدة فـ `/api/chat`. 12 حارس TDD RED ثم GREEN، Python 327 OK وAtulya 575 pass/3 skipped. |
| وكيل التقارير (J141) | `live_verified` بعد تشغيل محلي حقيقي | `wakil_reports` فـ أرشيف Atulya كيستقبل تقرير شامل من 17 ملف state + المانيفست، مرة كل 24 ساعة. المقترحات كيبقاو `proposed` فـ HUD حتى توافق؛ ما كاين أي تنفيذ ولا شبكة ولا سر. 10 حوارس TDD خضرة، وتمرير حي رجّع 1 رسالة و4 مقترحات معلّقة. |

التغييرات الجديدة كتدير commit/push بوتوماتيكيا بعد الجولة الخضراء، بموافقة صريحة منك. `:5100` و`:5000` أُعيد تحميلهم بموافقة صريحة: الـ HUD ولا كيعطي 15 قدرة، وصفحة `/health` ولا كتعرض `jarvis_backend_provider` كـ ℹ️ معلومة. الـ 20 S8 ولاو مسجّلين كـ endpoints خفيفة للـ brain المحلي بـ سندات قراءة فقط؛ الـ model trial باقي `needs_user_data` بصدق لأن الملفات الصغيرة غير موجودة محلياً. الجولة اليومية تفعّلت من دابا بـ `SUNNAVOK_DAILY_AGENTS` على الساعة 05:00. الـ passkey تّأكدات، والـ 10 قدرات القديمة كلها `live_verified`، بما فيهم `local-learning` و`chat-auth`. ما طلبنا منك لا كلمة مرور ولا سر، وما كتبنا أي سر فأي ملف، وما تدار أي SMS ولا مكالمة ولا فعل جهاز غير قراءة الحالة.
| استجابة Atulya (J143) | live_verified بالقياس الحي | جمل الحالة (`checking the systems`، `تحقق من النظام`، `Jarvis, quick status report on all systems`) كيتقرا من ملفات state عبر `web_intent` فـ 14–94ms، والـ SSE من :8501 و:3860 فـ 58–67ms. طلب وصف الكاميرا بلا صورة كيجاوب بصدق فـ 18ms. مهلة قاطعة `ATULYA_TURN_TIMEOUT=12` عبر `keep_alive.ps1`، وفال نموذج محلي فاضي/متوقف كيرجع تقرير state بدل «حاول مرة أخرى». TDD: 23/23 حارس مستهدف؛ الجولات Node 1091/1091، Python 332 OK، Atulya 582 pass/3 skipped، مانيفست 823. GSM باقي implemented_unverified بصدق غير 3 من 20 جهاز فيزيائي. |
| إلغاء GSM/Panda (J144) | live_verified بالجولات المحلية | بقرار المالك ولا GSM ولا Panda جزء من النظام: بوت `autonomous_checks.mjs` ما كيشغّل غير Node/Python/Atulya/المانيفست، بلا `src.gsm_bridge` ولا منفذ ADB. الحالة العامة ولا `live_verified` بـ15 قدرة محلية، و`gsm-fleet` + `gsm-model-trial` ولاو `not_available` بصدق في `gsm_status.json` و`gsm_workers.json` و`gsm_model_trial.json` بـ`cancelled=true`. مقترحات `gsm_relink_readonly` و`provide_on_device_model_locally` تّرفضو (`denied`) وأرشيف `action_audit.jsonl` كيسجّل القرار؛ الوكيل ما كيعاودش يقترحهم. TDD: 7/7 Node و6/6 Python مستهدفين. |
| جواب Atulya الصادق (J145) | TDD أخضر (17/17 مستهدف) | تقرير الحالة ما كيجيش إلا يلا طلب المالك واش من `web_intent` ولا من `_STATUS`؛ أي سؤال عادي (مثل `Home Depot on demo`) فاش النموذج المحلي كيتأخر ولا كيرجع فاضي كيجي جواب قصير صادق `model_busy`/`Local fallback` بلا `الحالة العامة` ولا جواب مكذوب، فـ SSE وغير SSE بالتساوي. طلبات الحالة باقية كتقرأ ملفات state محلية فـ `web_intent`. |
| سرعة النموذج المحلي (J146) | TDD أخضر (34/34 + 1 skipped) | التشخيص الحي بيّن أن :31416 كيجاوب فـ1.6s بلا tools، ولكن 73 أداة بـ28KB وصفات كتاخد 16.4s وفوق مهلة الـ12s. المزوّد المحلي loopback كيبعت دابا نفس الأدوات بوصفات مختصرة (80 حرف، و40 للوسائط) مع بقاء الأسماء والأنواع والـ required والـ enum؛ القياس ولا ~3s. المزوّد الخارجي باقي ما تبدّل. |
| سرعة النموذج المحلي (J147) | TDD أخضر (33/33 + 1 skipped) | سجل llama.cpp بيّن أن الطلب اللي كيتحمل 1339 token كيتاخد 73s فالـ CPU. الأدوات المحلية ولاو بلا أوصاف (نفس الأسماء والأنواع)، والدروس/الأفعال المحقونة فالـ system prompt تقلّصو لـ3+3 بـ100/50 حرف. كل محاولة توليد ولا لها سقف ATULYA_ATTEMPT_TIMEOUT=6s، وعند انتهاء مهلة المحاولة الأولى كتعاود الجولة بـ prompt مختصر وبلا أدوات قبل ما تعلن model_busy؛ الجولة كاملة باقية محدودة بـ12s. |
| سقف جواب الموديل المحلي (J148) | TDD أخضر (21/21) | سجل llama.cpp كيبين أن التوليد على هاد الجهاز كيجري بـ~4 tokens/s؛ 64 token كيتكلّفو 17s. المزوّد المحلي loopback ولا كيقصّر الجواب بـ ATULYA_LOCAL_MAX_TOKENS=24، والمزوّد الخارجي ما تبدّل. هادشي كيكمل J146/J147 باش الجواب العادي يبقى قصير ومحلي. |
| تدفّق الموديل المحلي (J149) | TDD أخضر (20/20) | راوتر :31416 كان كيقرأ الجواب كاملاً بـ response.read() قبل ما يرسلو، يعني stream كان بلا فائدة والتوليد البطيء (≈4 tokens/s) كيدوز 6s فـ Atulya. الراوتر دابا كيرحّل أسطر SSE فوراً بـ chunked و flush، والاختبار كيتحقق من وصول أول chunk قبل نهاية الجواب. |
| REST J1 — بوابة :5100 (J149) | TDD أحمر ثم أخضر (5/5) | وحدة api/rest_services.mjs كتقرأ وتكتب لوحة kanban من نفس ملف markdown ديال الخدمة Python، ومعها routes GET/POST على :5100 محمية بـ Origin loopback. الخدمة Python مازالة شغّالة حتى تتم الهجرة كاملة. |
| FreeLLMAPI أولاً، المحلي احتياطي (J150) | TDD أخضر (20/20) | بقرار المالك، خدمة :31415 ولات تُشغّل تلقائياً؛ Atulya كيجربها أولاً بـ `model=auto` (الراوتر كيختار الموديل المتاح تلقائياً) وإذا ما جاوبتش ولا ما كانش الإنترنت كيرجع للـ GGUF المحلي :31416 بلا سؤال. المفتاح كيبقى فملف state محلي (gitignore)، ما كيتكتبش فالمستودع ولا فـ .env. |
| FreeLLMAPI بلا أدوات (J151) | TDD أخضر (16/16) | الراوتر `auto` كان كيتأخر فأول token بسبب مخططات الأدوات؛ المزوّد الأساسي كيبعت دابا رسالة بلا أدوات، فالجواب كيجي فـ~1s (كان 6s+). الموديل المحلي كيبقى احتياطي بلا إنترنت وبنفس السقف 24 token. |
| فتح القدرات + تطوير ذاتي + 20 مشروع (J152) | TDD أحمر ثم أخضر (8/8 Node، 5/5 + 7/7 + 2/2 Python) | بقرار صريح من المالك: GSM/Panda وأفعال الأجهزة ولاو مفعّلين. فحص قراءة فقط بـ`adb devices -l` كشف 10 S8/S8+ و`gsm_bridge.scan()` كتب دليل `live_verified` بلا أخطاء؛ الـ20 اللي ذكرهم المالك ماشي كلهم موصولين دابا، والموديل الصغير على الجهاز باقي `needs_user_data`. ما كاين أي SMS/call بلا هدف ومحتوى صريحين. `auto_dev.py` كيعمل commit/push تلقائي غير يلا اختبارات node/python خضرة والمسارات بلا أسرار، و`autonome_evolve.py --daemon` ولا كيتشغّل من المراقب. 20 مشروع من تقرير آخر 7 أيام تنزّلو بـ`git clone --depth 1` فـ`esprieaether/state/imported_projects/` (مستبعد من Git والمانيفست)؛ ما كاينش pip/npm install ولا تنفيذ سكربتات مجهولة. تصحّح أيضاً عدّاد الدورات اللي كان كيتزاد مرتين. |
| تقرير GSM حي + daemon مستقر (J153) | TDD أحمر ثم أخضر (11/11 Node، 15/15 Python) | `autonomous_checks.mjs` ولا كيقرأ `gsm_status.json` و`gsm_model_trial.json` محلياً بدل ما يكتب «aucun appareil détecté» بشكل ثابت: الدليل الطازج (<=7 أيام) كيرفع `gsm-fleet` لـ`live_verified` بـ10 أجهزة، والدليل القديم أو الغائب كيبقى `needs_user_data` بلا اخضرار مخترع. اللوحة `:5100` ولا كتعرض `live_verified` بعد إعادة تشغيلها. وُجد أن كل خدمة فالـ venv ديال هاد الجهاز عندها process وسيط + ولد بنفس السطر (ما كاينش تكرار حقيقي)، فما تقتلش أي واحد منهم؛ المشكلة الحقيقية كانت `UnicodeEncodeError` فكتابة سجل الداemon، وكل `open()` ولا كيصرّح بـ`utf-8`. تصحّح أيضاً `auto_dev.py` اللي كان كيشغّل اختبارات Python من جذر المستودع بدل `esprieaether`، فكان كيمنع الـ commit خطأً. وكل أوامر `git` فالحارس ولا كيقراو بـ`utf-8`، فما كيضيعش رقم الجولة كي كيجي فSubject حرف غير ASCII. و`auto_dev` كيتجاهل ملفات الحالة القرينية (`autonome_evolve_state.json`) وكيعمل `git add -- <paths>` ماشي `add -A`، فما كيولّدش commit فاضي كل 5 دقائق. |
| REST phase 2 + لوحة GSM حية (J154–J158) | TDD أحمر ثم أخضر (Node 7/7 جديد + 22/22 اللوحة، Python 7+7+9+6) | بقرار المالك نبدأو بالأربع مسارات غير بالآمن. (`1`)routes `/api/rest/gsm/status` و`/api/rest/integrations/list` و`/api/rest/homedock/widgets` ولاو كيقراو ملفات محلية بلا خدمة Python؛ الدليل القديم كيتدهور لـ`implemented_unverified` مع `alert=expired`، والغائب `needs_user_data`. لوحة `:5100` وHUD `:3860` ولاو كيعرضو حالة GSM الحقيقية (10 موصولين، SIM جاهزة، الموديل الصغير). مراقب `gsm_watcher.py` كيدير scan قراءة فقط غير كي غاب الدليل ولا فات 7 أيام، وكيعطي تنبيه فاش فشل، وكتتبع متى وصل الـ20. (`2`) سرّعنا الحساب: inventaire ديال 18,836 ملف فـ Atulya كان كيتحسب فكل طلب؛ ولا مخزّن 30 ثانية، والـ HUD كيجي فـ~1s. (`3`) مجلد `esprieaether/state/gsm_model/` ولا هو المكان الرسمي للبinaire arm64 ELF والـGGUF ≤600MB اللي كيجيبهم المالك، بلا تنزيل؛ وجودهم كيعطي `implemented_unverified` و`ready=true` ماشي `live_verified` قبل benchmark. (`4`) `gsm_actions.py` كيحقق من موافقة `approved_once` بفاعل معروف، نوع مسموح، مفتاح صريح من المالك، SIM `READY`، مستلم ورسالة صريحين؛ ما كاين أي مُنفّذ، أي SMS/call، أي `subprocess` ولا لمس للanceur USB. كل البوابات مغلقة دابا: لا SIM ولا إذن صريح. |
| إصلاح صوت Atulya (J159) | TDD أحمر ثم أخضر (Node 6/6 جديد، Python 8/8) | شكوى المالك: «أتوليا عندو مشكل فالصوت، ما كنسمعوش». السبب بعد التشخيص: المتصفح كيمنع تشغيل الصوت قبل أول ضغطة، و`playBlob` كان كيدوز الصوت عبر `AudioContext` suspended بـ`createMediaElementSource` (صوت مقطوع على Chrome/Windows)، والمتصفح ما عندوش صوت `ar-MA` فكان كيسقط صامتاً. `assistant.js` ولا كيحتفظ بأول جواب وكيطلقو عند أول `pointerdown`/`keydown`، وكيلعب الـblob مباشرة بـ`new Audio()` بلا `AudioContext`، وكيلاقي أي صوت مثبّت (Zira `en-US`) بدل ما يبقى بلا صوت. HUD `:3860` ولا فيه كبسة «شغّل جملة» كتطلب WAV من خدمة محلية `:5105` عبر `/local-voice/` بـGET (بلا POST ولا onclick، حفاظاً على قاعدة HUD) بلا CORS ولا سحابة؛ الخدمة كتستعمل نفس موديل Supertonic المحلي، كتكتب دليلاً فـ`state/voice_output_evidence.json` بـ`implemented_unverified` و`playback=owner_confirmation_pending` (ما كندّعيش أنك سمعتها). الدليل الحي: WAV Darja 252446 بايت، 44.1kHz، 2.86s، peak 13093 / rms 1813، غير صامت؛ `/health` و`/local-voice/health` راجعين `live_verified` للمحرك، والسماع الفعلي باقي بانتظار تأكيد المالك. `voice_daemon.py` باقي مطفّى افتراضياً، والـlock القديم ما تلمّس، وما كاين أي ميكروفون ولا SMS/call ولا لمس لـ`touping.exe`. تّصلح أيضاً أثر جانبي: كود `unlockSound` كان داخل المقطع اللي كيقرّيه `tests/voice/test_web_speech_split.py` فـNode بلا DOM، فنقلناه قبل `speakWithBrowser`؛ ومهلة اختبار `test_optional_voice_import` ولاو 90s بدل 30s (الاستيراد كياخد ~28s، و30s كانت كتفشل فالضغط). |