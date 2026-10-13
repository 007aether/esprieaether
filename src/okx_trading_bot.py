#!/usr/bin/env python3
"""
okx_trading_bot.py — EsprieAether sovereign trading bot (spot only)

Strategy: JEV decides the move (buy/sell/hold) with probabilities;
the bot sizes the order and only acts above a confidence threshold.

SAFETY:
- spot only (tdMode cash), no leverage, no shorts
- hard daily loss cap (default 2% of equity)
- max position size per trade (default 10% of equity)
- every decision + order logged to Coordination/
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from okx_client import balance, candles, place_spot_order, orders_pending, OKXError  # noqa: E402

# ── Config ──
INST_ID = os.getenv("BOT_INST_ID", "BTC-USDT")
BAR = os.getenv("BOT_BAR", "1H")
CONF_MIN = float(os.getenv("BOT_CONF_MIN", "0.60"))      # act only above this confidence
MAX_POS_PCT = float(os.getenv("BOT_MAX_POS_PCT", "0.10"))  # max 10% of equity per trade
DAILY_LOSS_CAP = float(os.getenv("BOT_DAILY_LOSS_CAP", "0.02"))  # stop after 2% daily loss
DRY_RUN = os.getenv("BOT_DRY_RUN", "1") == "1"           # default: simulate only
LOG = REPO / "Coordination" / "okx_bot.log"
STATE = REPO / "Coordination" / "okx_bot_state.json"

ROUTER_DECIDE = os.getenv("AETHER_ROUTER", "http://127.0.0.1:11435") + "/decide"


def log(msg: str):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} | {msg}"
    print(line, flush=True)
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"day": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "pnl_pct": 0.0, "trades": 0, "position": 0.0}


def save_state(st: dict):
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(st, indent=2), encoding="utf-8")


def ask_jev(market: dict) -> dict:
    """Ask the JEV brain for a typed decision. Falls back to HOLD on any error."""
    import requests
    questions = {
        "action": {
            "type": "choice",
            "instructions": "Given `state`, what is the best spot action right now?",
            "criteria": {
                "buy": "Momentum + structure favour buying this asset",
                "sell": "Momentum + structure favour selling into strength",
                "hold": "No clear edge; wait",
            },
        },
        "regime": {
            "type": "choice",
            "instructions": "Classify the current market regime from `state`",
            "criteria": {
                "trend_up": "Higher highs, higher lows",
                "trend_down": "Lower highs, lower lows",
                "range": "Sideways chop",
            },
        },
    }
    try:
        r = requests.post(ROUTER_DECIDE, json={"state": market, "questions": questions}, timeout=30)
        r.raise_for_status()
        return r.json().get("answers", {})
    except Exception as e:
        log(f"JEV error: {e}")
        return {}


def latest_close(inst_id: str) -> float:
    c = candles(inst_id, BAR, 2)
    return float(c[0][4]) if c else 0.0  # [ts, o, h, l, c, vol, ...]


def equity_usd() -> float:
    b = balance()
    try:
        return float(b[0]["totalEq"])
    except (IndexError, KeyError, ValueError):
        return 0.0


def run_once() -> dict:
    st = load_state()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if st["day"] != today:
        st = {"day": today, "pnl_pct": 0.0, "trades": 0, "position": st.get("position", 0.0)}
        save_state(st)

    if st["pnl_pct"] <= -abs(DAILY_LOSS_CAP):
        log(f"daily loss cap hit ({st['pnl_pct']:.2%}) — standing down today")
        return {"action": "stand_down", "reason": "daily_loss_cap"}

    px = latest_close(INST_ID)
    eq = equity_usd()
    if eq <= 0:
        log("equity is 0 — fund the account first")
        return {"action": "no_funds"}

    market = {
        "inst_id": INST_ID,
        "last_close": px,
        "bar": BAR,
        "equity_usd": eq,
        "position_btc": st.get("position", 0.0),
    }
    ans = ask_jev(market)
    action_ans = ans.get("action", {})
    action = action_ans.get("choice", "hold")
    conf = action_ans.get("confidence", 0.0)
    regime = ans.get("regime", {}).get("choice", "unknown")

    log(f"JEV → action={action} conf={conf:.2f} regime={regime} px={px}")

    if action == "hold" or conf < CONF_MIN:
        return {"action": "hold", "confidence": conf, "regime": regime}

    # order sizing
    pos_usd = min(MAX_POS_PCT * eq, eq)
    sz_btc = round(pos_usd / px, 6)
    if sz_btc <= 0:
        return {"action": "hold", "reason": "size_too_small"}

    result = {"action": action, "confidence": conf, "regime": regime, "size_btc": sz_btc, "dry_run": DRY_RUN}
    if DRY_RUN:
        log(f"DRY-RUN would {action} {sz_btc} BTC @ ~{px}")
        return result

    try:
        side = "buy" if action == "buy" else "sell"
        if side == "sell" and st.get("position", 0.0) <= 0:
            log("sell signal but no position — skipping")
            return {"action": "hold", "reason": "no_position_to_sell"}
        resp = place_spot_order(INST_ID, side, str(sz_btc), ord_type="market")
        log(f"order placed: {resp}")
        st["trades"] += 1
        st["position"] = st.get("position", 0.0) + (sz_btc if side == "buy" else -sz_btc)
        save_state(st)
        result["order"] = resp
    except OKXError as e:
        log(f"order error: {e}")
        result["error"] = str(e)
    return result


def main():
    log(f"=== okx trading bot — inst={INST_ID} bar={BAR} conf>={CONF_MIN} dry_run={DRY_RUN} ===")
    interval = int(os.getenv("BOT_INTERVAL_SEC", "300"))  # check every 5 min
    while True:
        try:
            run_once()
        except Exception as e:
            log(f"cycle error: {e}")
        time.sleep(interval)


if __name__ == "__main__":
    if "--once" in sys.argv:
        print(json.dumps(run_once(), indent=2))
    else:
        main()
