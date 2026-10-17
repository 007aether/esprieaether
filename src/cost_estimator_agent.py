#!/usr/bin/env python3
"""
⚡ EsprieAether - Sunna Cost Estimator Agent
=====================================
بوت estimation ذكي للمصنع الحديدي (Sunna):
    galvanisation  45 DH/kg (limit 80.0)   ← fixed budget real price
    steel          12 DH/kg (limit 40.0)
    labor          80 DH/hour
    margin         35%
    TVA            20%

OS:_local:app  =  subtotal + TVA + margin
PERFECT:  total < 25000 DH   → viable
         25000–45000 DH     → verify mould + charging
         > 45000 DH         → request refund / re-supply

Usage:
    python cost_estimator.py estimate <weight_kg> <qty> [--galva <dh_kg>] [--steel <dh_kg>]
    python cost_estimator.py sanity
    python cost_estimator.py data
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA = BASE_DIR / "data"
ESTIMATE_FILE = DATA / "cost_estimator_log.json"
LOGS = DATA / "logs"
LOGS.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("sunna_cost")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOGS / "cost_estimator.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

# ── Real price model (from current market, MAD) ──────────────────────────
MODEL = {
    "galvanisation": {"dh_per_kg": 45.0, "max_limit": 80.0, "note": "real quoted price ~45 DH/kg"},
    "steel":        {"dh_per_kg": 12.0, "max_limit": 40.0, "note": "mild steel coil price"},
    "labor":        {"dh_per_hour": 80.0, "note": "manual + press operation"},
    "margin":       {"percent": 35.0, "note": " entrepreneurship + warranty margin"},
    "tva":          {"percent": 20.0, "note": "Moroccan TVA on supplier price"},
}

# ── Sanity caps (reject absurd prices) ────────────────────────────────────
MAX_GALVA_DH_KG = 80.0
MAX_STEEL_DH_KG = 40.0


def clean_number(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def estimate(weight_kg: float, qty: int = 1,
             galva_price: float | None = None,
             steel_price: float | None = None) -> dict:
    """Return line-by-line cost estimate for galvanised steel parts."""
    g = clean_number(galva_price if galva_price is not None else MODEL["galvanisation"]["dh_per_kg"])
    s = clean_number(steel_price if steel_price is not None else MODEL["steel"]["dh_per_kg"])

    # sanity caps
    g = min(g, MAX_GALVA_DH_KG)
    s = min(s, MAX_STEEL_DH_KG)
    g = max(g, 1.0)
    s = max(s, 1.0)

    galva_kg = weight_kg * 0.65          # galvanised is ~65% of gross weight
    steel_kg = weight_kg * 0.35          # steel core is ~35%
    galva_dh = galva_kg * g
    steel_dh = steel_kg * s
    labour_dh = (weight_kg * 1.5) * MODEL["labor"]["dh_per_hour"]  # 1.5 h per 1kg ideal
    subtotal = galva_dh + steel_dh + labour_dh
    margin_dh = subtotal * (MODEL["margin"]["percent"] / 100.0)
    tva_dh = (galva_dh + steel_dh + labour_dh) * (MODEL["tva"]["percent"] / 100.0)
    total = subtotal + margin_dh + tva_dh
    unit_price = total / qty

    viable = "OK" if total < 25000 else ("VERIFY" if total <= 45000 else "REJECT")
    return {
        "estimate_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {"weight_kg": weight_kg, "qty": qty,
                   "galva_price": g, "steel_price": s},
        "calculations": {
            "galva_kg": round(galva_kg, 2),
            "steel_kg": round(steel_kg, 2),
            "galva_dh": round(galva_dh, 2),
            "steel_dh": round(steel_dh, 2),
            "labour_dh": round(labour_dh, 2),
            "subtotal": round(subtotal, 2),
            "margin_dh": round(margin_dh, 2),
            "tva_dh": round(tva_dh, 2),
            "total": round(total, 2),
            "unit_price": round(unit_price, 2),
        },
        "viability": viable,
        "notes": {
            "galvanisation": MODEL["galvanisation"]["note"],
            "steel": MODEL["steel"]["note"],
            "labor": MODEL["labor"]["note"],
            "margin": MODEL["margin"]["note"],
            "tva": MODEL["tva"]["note"],
        },
    }


def sanity() -> dict:
    """Sanity check on the price model (no math)."""
    ok = True
    if MODEL["galvanisation"]["dh_per_kg"] > MAX_GALVA_DH_KG:
        ok = False
        logger.warning("⚠️ galvanisation price above safety cap")
    if MODEL["steel"]["dh_per_kg"] > MAX_STEEL_DH_KG:
        ok = False
        logger.warning("⚠️ steel price above safety cap")
    return {"model_ok": ok, "caps": {"MAX_GALVA": MAX_GALVA_DH_KG, "MAX_STEEL": MAX_STEEL_DH_KG}}


def _log(entry: dict):
    try:
        LOGS.joinpath("cost_estimator.log").parent.mkdir(parents=True, exist_ok=True)
        with open(LOGS / "cost_estimator.log", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def main():
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "sanity"
    if cmd == "sanity":
        print(json.dumps(sanity(), ensure_ascii=False, indent=2))
    elif cmd == "estimate":
        weight = clean_number(sys.argv[2]) if len(sys.argv) > 2 else 1.0
        qty = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        r = estimate(weight, qty)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        _log(r)
    elif cmd == "data":
        print(json.dumps({"model": MODEL, "caps": {"MAX_GALVA": MAX_GALVA_DH_KG,
                    "MAX_STEEL": MAX_STEEL_DH_KG}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
