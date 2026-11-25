# Retour d'expérience — Hacker News → ESPRIEATHER (25/11/2026)

30 histoires lues depuis `https://news.ycombinator.com/`. Voici ce qui a été
réellement intégré, ce qui est seulement noté, et ce qui est écarté. Aucun
téléchargement cloud, aucune clé, aucun paiement, aucune distillation.

## Intégré et vérifié (J92)

| # | Histoire | Action dans le projet |
|---|---|---|
| 3 | Models Can Communicate via Inference Servers Despite Being Sandboxed | `esprieaether/src/egress_guard.py` : tout hôte de modèle doit être loopback (`assert_loopback_url`). |
| 8 | Taking over US Treasury subdomains for $3 each | `open_website` refuse loopback, IP privées, `.local`/`.internal` et liens avec identifiants. |
| 18 | Serving Qwen via AWS Lambdas for fun and 80x negative profit | Le pont Jarvis ne peut plus viser un serveur distant : coût cloud impossible par construction. |
| 21 | Active intrusion campaign against Check Point servers | Même garde appliquée aux URL publiques ; aucune preuve publique ne contient de secret ou d'hôte interne. |
| 27 | Ask HN: accuser de distillation | `egress_selfcheck.json` enregistre uniquement des preuves locales et des URL testées ; aucune affirmation d'entraînement externe. |

Nouvelle capacité HUD : `local-egress-guard`, `live_verified` seulement avec une
preuve fraîche (TTL 7 jours) dans `esprieaether/state/egress_selfcheck.json`.

TDD : rouge sur 14 tests Python + 4 sous-tests Atulya + 1 test Node, puis vert
sur les mêmes tests.

## Noté, pas encore exécuté (honnête)

| # | Histoire | État |
|---|---|---|
| 1 | Matrix Multiplication Θ(n^2.25) | lecture de recherche, pas de code |
| 5 | Ternary Bonsai 2.5 27B | idée de catalogue de modèles ; `needs_user_data` (pas de 27B local) |
| 9 | Marginalia Search | déjà couvert par le BM25 local du vault |
| 11 | Open problems classés par LLM | backlog documentaire, pas de service externe |
| 13 | Versine : MCP pour envoyer/recevoir de l'argent | écarté : nécessiterait identifiants, paiement et égress |

## Écarté comme non pertinent pour un assistant 100 % local

2, 4, 6, 7, 10, 12, 14, 15, 16, 17, 19, 20, 22, 23, 24, 25, 26, 28, 29, 30.

Règle appliquée : une histoire n'est intégrée que si elle améliore la confidentialité,
la vérifiabilité ou la robustesse hors ligne. Sinon elle reste une lecture, pas une
fonctionnalité inventée.
