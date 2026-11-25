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
  **782 fichiers** inventoriés, ajout au manifest des modules locaux, des outils
  Atulya et des rapports d'analyse.
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
- **Traduction des documents de test** : les assertions de `briefing_settings`
  suivent le nouveau libellé darija du briefing matinal.

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
| Barge-in | aucun événement `barge_in` réel enregistré | `implemented_unverified` |
| Éveil vocal | essai micro réel 12 s sur `hey_jarvis_v0.1.onnx` : `hits=0`, `peak=0.053711` (seuil 0.18), entrée `1` = `Microphone (Realtek(R) Audio), MME` ; mesure séparée `peak=0.011353`, `RMS=0.000767` → `wake_selfcheck.json` `ok=false` | `implemented_unverified` |
| Interface darija | HUD, panneaux, musique, réglages et briefing sans libellés anglais visibles | `live_verified` |
| Page autonome / fenêtre flottante | `/atulya/` local + fenêtre déplaçable, sans CDN ni `onclick` | `live_verified` |
| Approbation HUD | aucun `PUT` loopback réel dans `action_audit.jsonl` | `implemented_unverified` |
| Sources documentaires | aucun dossier `legal`/`fiscal`/`travail` fourni | `needs_user_data` |
| MCP externe | aucun endpoint HTTPS externe fiable ni octroi outil-par-outil fourni | `needs_user_data` |

## Tests

- Node : **1058 pass / 0 fail** sur 68 fichiers `tests\*.test.mjs`,
  dont le test d'origine du pont `J100`, le contrôle darija des pages
  `jarvis.html` / `system.html`, le délai `120000` du relais, la fermeture
  clavier de la fenêtre flottante, les contrôles J106/J108 et le contrôle J110
  des services en démarrage manuel.
- Node ciblé (pont, darija, install/update) : **157/157** (155 + les 2 contrôles J106/J108).
- Python unittest : **250 tests OK / 0 fail** (246 + J110), dont le service
  sentinel qui ne traite plus `dsh_bridge` et `llm_gateway` comme des erreurs.
- Atulya pytest : **566 passed, 3 skipped**, 16 subtests passés (0 fail),
  dont les 7 contrôles darija (J105) et les 6 nouveaux contrôles J106/J109
  (journal sans secret, reprise de flux, erreurs d'outils, plafond de résultat,
  compression de l'historique). La dernière re-vérification pytest est bloquée
  par l'absence du module local `webauthn` dans cet interpréteur, sans lien avec
  ces changements ; le résultat 566 reste celui de la passe validée.
- Aucun upload, token cloud ou clé externe.

## شنو ناقص (MADA YANKOSONA)

> كل اللي كيتطلب بيانات ديالك أو جهاز حقيقي، ما تدارش بلا طلب صريح منك.

| العنصر | الحالة | شنو كيتطلب باش يتحقق |
|---|---|---|
| `external_mcp` | `needs_user_data` | عنوان HTTPS خارجي حقيقي + منح كل أداة علىحدة بعد `Test & discover tools`. |
| `documentary-sources` | `needs_user_data` | مسارات حقيقية لملفات `legal` / `fiscal` / `travail` باش يتحسب SHA-256 ديالها. |
| APK / جهاز `iip` | `needs_user_data` | APK أو ربط جهاز أندرويد؛ الجهاز دابا `offline`، `seen=0`، وطلب `ping` مصفوف بلا إيصال. ما تدار أي فعل جهاز. |
| `barge-in` | `implemented_unverified` | حدث `barge_in` حقيقي أثناء الكلام؛ الميكرو ما عطاش إشارة فوق العتبة 0.18. |
| سجل توقف الجواب | `implemented_unverified` | أول توقف حقيقي كيكتب سطر فـ `brain_errors.jsonl`؛ الاختبارات غطّات الحالات، ولكن ما وقعش توقف جديد فالسيرفر الحي بعد TDD. |
| `atulya-wake` | `implemented_unverified` | كلمة إيقاظ حقيقية تطلع `hits>0` فـ `wake_selfcheck.json`؛ التجربة الأخيرة 12 ثانية عطات `hits=0`. |
| موافقة HUD | `live_verified` | `action_audit.jsonl` فيه `act-9ec94b52eb`: `proposed->approved_once` فـ `2026-11-25T09:03:37.179Z` من `hud`. |
| تنبيهات `guard_failed/python` و`guard_failed/endpoints` | `implemented_unverified` | الإصلاحات تكتبو، ولكن الحارس والمشغل الحي مازالو كيقراو الكود القديم؛ كيتطلب إعادة تحميل بلا restart بلا موافقة صريحة. |
| عدّاد `failed_runs` / `timed_out_runs` التراكمي | `implemented_unverified` | ولا معلومة فالـ dashboard؛ الإنذار كيبقى للفشل القريب غير. كيتطلب إعادة تحميل `api/server.mjs`. |
| self-heal ديال الـ supervisor | `implemented_unverified` | إعادة تحميل `keep_alive.ps1` باش يقرأ الإصلاح الجديد؛ ما تدارش restart بلا موافقة صريحة. |
| `/api/chat` غير-streaming | تحسّن بعد موافقة | الـ `timeout` ولا `120000` فـ `serve_g0dm0d3.mjs`، الـ UI كيستعمل streaming. |
| محادثة كاملة بمصادقة | غير متحقق | كيتطلب passkey ديال المالك؛ تحققنا غير بـ `401 {"detail":"Sign in with your Atulya passkey to continue."}` بدل `403`. هاد الـ `401` هو بوابة المصادقة العادية على `/api/*` (ما كاينش خطأ)، والـ `/api/health` كيرجّع `200`. |
| حزمة unittest محلية (root) | تحقّق بعد J110 | **250 passed / 0 fail**؛ كان فيها اختبار واحد كيتوقع صيغة فرنسية قديمة فـ `persona.py`، تصلّح باش يقرأ الدارجة بحروف عربية. |

اللي تقدر تعطيني دابا: عنوان MCP خارجي، مسارات المستندات، APK/جهاز مربوط، ولا passkey للتحقق من المحادثة. غير ما تعطينيش كلمات مرور ولا أسرار فالملفات.
