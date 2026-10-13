# 🧩 16 GitHub Integrations — EsprieAether × Sunna

Cloned to `~/AppData/Local/Temp/new_repos/`. Each gets linked under
`esprieaether/integrations/<name>/` and mapped to a role in the stack.

| # | Project | What it is | EsprieAether role | Sunna role | Priority |
|---|---------|-----------|-------------------|-----------|----------|
| 1 | **mimic** (littledivy) | Intercept any app → Python client via AI | Auto-generate API clients (OKX, Netlify, GMB) without hand-writing | Auto-devis from any supplier site | 🟡 med |
| 2 | **Checkmate** (bluewave-labs) | Uptime monitoring (Datadog alt) | Watchdog for the 7 services + public sites | Watch the live Netlify site 24/7 | 🔴 high |
| 3 | **Portracker** (mostafa-wahied) | Discovers running services + ports | Live port map (11435/11436/5000/5001/5100/5101/8000) | Show workshop network devices | 🟢 easy |
| 4 | **Ask4Me** (easychen) | Human-in-the-loop HTTP approvals | Approve risky bot actions (OKX orders, deploys) via Telegram | Approve devis before sending | 🟡 med |
| 5 | **Outline** (easychen) | Knowledge base / wiki | Team docs for EsprieAether (agents, skills, playbooks) | Sunna SOPs (devis, production, legal) | 🟡 med |
| 6 | **HomeDock OS** | Homelab OS / dashboard | Alt control center (self-hosted) | Workshop dashboard (catalogue, orders) | 🟢 easy |
| 7 | **FrankMD** (akitaonrails) | Markdown blog editor (no DB) | Publish agent learnings / ECC notes | Sunna blog (SEO → customers) | 🟢 easy |
| 8 | **Invoice Builder** (piratuks) | Offline invoicing → PDF | — (we have devis_builder) | **Upgrade devis_builder** → real PDF invoices | 🔴 high |
| 9 | **Octelium** (octelium) | Zero-trust access / VPN / gateway | Secure the 7 services (public exposure) | Remote workshop access | 🟡 med |
| 10 | **Kino** (mmcdole) | Terminal Plex/Jellyfin client | Media control from CLI | — | 🟢 easy |
| 11 | **PriceGhost** (clucraft) | AI price tracker | Track OKX/crypto prices | **Track steel/galvanisation prices** | 🔴 high |
| 12 | **Veritas Kanban** (BradGroux) | Markdown kanban + agent integration | Task board for the 7 agents | Sunna production board (orders → done) | 🟡 med |
| 13 | **xPrivo** (xprivo) | Privacy-first AI chat (local) | Alt chat UI for JARVIS/router | Customer-facing AI assistant | 🟡 med |
| 14 | **Cronpulse** (techfort) | Cron job monitor + alerts | Alert if veille/offres/netlify bots die | Alert if souk/offres bots die | 🔴 high |
| 15 | **Homescreen-hero** (trentferguson) | Plex dashboard + widgets | Media dashboard | — | 🟢 easy |
| 16 | **frankmd** (dup of FrankMD) | — | — | — | skip |

## 🎯 Top 5 to wire first (high value, low effort)

1. **Cronpulse** → monitor all 12 Sunna bots + 7 services, alert to Telegram
2. **Checkmate** → uptime for the live Netlify site + public services
3. **Invoice Builder** → real PDF invoices for Sunna (replaces devis text)
4. **PriceGhost** → track steel/galva prices (fills the #2 blocker: devis cost)
5. **Portracker** → live port map in the control center

## 🔌 How each gets wired

- `integrations/<name>/` = junction to the cloned repo (gitignored)
- A small adapter under `src/integrations/<name>_adapter.py` exposes it as
  a Flask route or background bot
- Watchdog learns the new health endpoints
- Control center gets a new card
- Telegram gets a `/integration <name>` command
