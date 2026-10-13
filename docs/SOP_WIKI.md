# 📚 SOP Wiki — EsprieAether × Sunna

> Outline-style knowledge base (markdown, no DB). Every agent reads this
> before acting. Update it whenever a procedure changes.

---

## 🏭 SUNNA — Standard Operating Procedures

### SOP-01 · Devis (عرض الثمن)
1. Check live prices: `/sunnaprix` or `Recherche/live_prices.json`
2. Build: `python bots/devis_builder.py --client "<name>" --product "<prod>" --qty <n>`
3. Output: `Devis/Devis_<client>_<date>.pdf` (HT + TVA 20% + TTC)
4. Valid 30 days. Send signed back.
5. Log in `Coordination/HANDOFF.md`.

### SOP-02 · Galvanisation quote
- Call Galvafer: **0522 67 46 31**
- Get price per kg → update `Recherche/live_prices.json` (galvanisation)
- Re-run devis with the real number.

### SOP-03 · Daily routine
| Time | Bot | Output |
|---|---|---|
| 07:30 | Al_Afdal | full report |
| 08:30 | Souk_Bot | material + market prices |
| 09:00 | Offres_Bot | tenders/opportunities |
| every 6h | veille_bot | GitHub watch |
| every 6h | sunna_price_tracker | steel/galva/zinc |

### SOP-04 · Live site
- URL: `Coordination/netlify_url.json`
- keepalive bot re-drops every 25 min if unclaimed
- To make permanent: claim on app.netlify.com (007aether)

---

## ⚙️ EsprieAether — Operations

### SOP-10 · Restart everything
```bash
cd ~/Desktop/esprieaether
./esprieaether_24_7.bat        # starts all 8 services
# watchdog keeps them alive; heartbeat alerts Telegram on death
```

### SOP-11 · Service map
| Port | Service |
|---|---|
| 11434 | ollama |
| 11435 | router (6 brains, 13 models, 7 agents) |
| 11436 | orchestrator |
| 5000 | web + /control |
| 5001 | cloud-desktop (+ /tor /integrations /api/okx) |
| 5100 | sunna-api |
| 5101 | dsh-bridge |
| 5102 | integrations-adapter |
| 8000 | JARVIS OSINT |

### SOP-12 · JEV decision
```bash
curl -X POST http://127.0.0.1:11435/decide -H "Content-Type: application/json" -d '{
  "state": {"message": "..."},
  "questions": {"q": {"type": "choice", "instructions": "...",
    "criteria": {"a": "...", "b": "..."}}}
}'
```

### SOP-13 · OKX
- connector: `src/okx_client.py` (withdrawal refused by code)
- trading bot: `src/okx_trading_bot.py` (DRY-RUN until funded)
- live switch: `BOT_DRY_RUN=0` after account has funds

### SOP-14 · Telegram commands
`/status` `/sunna` `/sunnabilan` `/sunnadevis` `/sunnaprix` `/sunnanetlify`
`/jarvis` `/tm` `/integrations` `/okx`

---

## 🔒 Rules
1. Never put API keys in chat — env vars / .env only.
2. Never type a password on the user's behalf.
3. Withdrawal endpoints are code-blocked.
4. Log every agent action in `Coordination/HANDOFF.md`.
5. Cost: 0 MAD — free models only.
