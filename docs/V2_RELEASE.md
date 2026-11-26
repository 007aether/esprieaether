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
  **806 fichiers** inventoriés, ajout au manifest des modules locaux, des quatre
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
| HUD des nouveaux agents | 13 capacités après rechargement de `:5100` : `github-scout`, `doctor`, `rea` ajoutés aux 10 existantes avec preuve TTL 7 jours | en attente de rechargement |

## Tests

- Node : **1069 pass / 0 fail** sur 71 fichiers `tests\*.test.mjs` (dont J114,
  J115 et les 3 contrôles `jarvis_new_agents.test.mjs`), dont le test d'origine
  du pont `J100`, le contrôle darija des pages `jarvis.html` / `system.html`,
  le délai `120000` du relais, la fermeture clavier de la fenêtre flottante,
  les contrôles J106/J108, le contrôle J110 des services en démarrage manuel,
  les 2 contrôles J111 du relais et du lanceur Claude Code local, et les
  contrôles d'installation du manifeste à 806 fichiers.
- Node ciblé (pont, darija, install/update) : **157/157** (155 + les 2 contrôles J106/J108).
- Python unittest : **306 tests OK / 0 fail**, dont 259 tests de base (J110 à
  J114), 9 contrôles du docteur, 4 contrôles d'auto-réparation (J123), 7 contrôles
  de la veille GitHub (dont CLI cp1252 et reprise 403/429), 6 contrôles de
  l'ordonnanceur, 6 contrôles `rea` + 4 compatibilité, 4 contrôles du registre
  des agents et 3 contrôles d'apprentissage depuis la veille (J122/J127, listes et comptages). Aucun test
  supprimé ni affaibli.
- Atulya pytest : **566 passed, 3 skipped**, 16 subtests passés (0 fail),
  dont les 7 contrôles darija (J105) et les 6 nouveaux contrôles J106/J109
  (journal sans secret, reprise de flux, erreurs d'outils, plafond de résultat,
  compression de l'historique). Passe rejouée dans le `.venv` local avec
  `webauthn` installé et le Node local `.tools\node-v26.13.1` sur `PATH` ;
  le premier essai sans ce Node avait donné un faux `test_web_ui_still_needs_approval`
  (« Node is unavailable »), corrigé par le `PATH` sans toucher au code.
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
| HUD بـ 13 قدرة | `implemented_unverified` فالملفات | `api/server.mjs` و`espria_system.py` فيهما `github-scout` و`doctor` و`rea` بـ evidence وTTL 7 أيام؛ خدمة `:5100` الشغّالة مازالة كتعطي 10 قدرات لأن الكود القديم محمّل فالذاكرة. إعادة التحميل كتطلب موافقة صريحة جديدة. |

اللي باقي غير: (1) إعادة تحميل `:5100` باش يظهرو الـ 13 قدرة فالـ HUD الحي، و(2) commit/push للتغييرات الجديدة. كيهربو على موافقة صريحة منك، والجولة اليومية تفعّلت من دابا بـ `SUNNAVOK_DAILY_AGENTS` على الساعة 05:00. الـ passkey تّأكدات، والـ 10 قدرات القديمة كلها `live_verified`، بما فيهم `local-learning` و`chat-auth`. ما طلبنا منك لا كلمة مرور ولا سر، وما كتبنا أي سر فأي ملف، وما وقّعنا ولا دفعنا ولا أعدنا تحميل أي خدمة بلا إذن جديد.
