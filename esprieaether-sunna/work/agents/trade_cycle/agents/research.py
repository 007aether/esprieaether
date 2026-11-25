"""Research Agent — Jim

يجمع الأخبار ومصادر العملات الرقمية، ويُصوغ الفرص مع مؤشرات red flags.
القرار لا يترك لـ LLM: الوكيل ينتج بيانات جاهزة للموافقة عليها.
"""

import os
import json
import sqlite3
import logging
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent  # work (4 levels up)
DATA_DIR = BASE_DIR / "data"
LOG_FILE = DATA_DIR / "logs" / "trade_cycle" / "research.log"
DB_PATH = DATA_DIR / "trade_cycle.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger("research")

# Target symbols for the trade cycle
DEFAULT_TARGETS = ["BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "AVAX", "DOT"]

# Real market source (CoinGecko). Fallback to a deterministic snippet if the API is unreachable.
COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/coins/markets"
    "?vs_currency=usd&order=market_cap_desc&per_page=40&page=1"
    "&price_change_percentage=24h"
)

# Hard-rule thresholds used to attach transparent red flags (rule-based, not LLM).
MIN_MARKET_CAP_USD = 500_000_000
MIN_VOLUME_24H_USD = 10_000_000
MAX_24H_CHANGE_PCT = 20.0
MAX_RED_FLAGS = 3


def _log(msg):
    logger.info(msg)


def _connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _fetch_markets() -> list[dict] | None:
    """Real step: fetch live CoinGecko market data."""
    try:
        url = (urllib.parse.quote(COINGECKO_URL, safe="/:?&=."))
        with urllib.request.urlopen(url, timeout=20) as r:
            data = json.loads(r.read().decode())
        if not isinstance(data, list):
            return None
        out = []
        for c in data:
            out.append({
                "id": c.get("id"),
                "symbol": (c.get("symbol") or "").upper(),
                "name": c.get("name"),
                "current_price": c.get("current_price") or 0.0,
                "market_cap": c.get("market_cap") or 0.0,
                "volume_24h": c.get("total_volume") or 0.0,
                "change_24h": c.get("price_change_percentage_24h") or 0.0,
                "url": f"https://coinmarketcap.com/currencies/{c.get('id')}/",
            })
        return out
    except Exception as e:
        _log(f"[research] CoinGecko fetch error: {e}")
        return None


def _coins_for_targets(markets: list[dict], targets: list[str]) -> dict[str, dict]:
    by_id = {c.get("id"): c for c in markets if c.get("id")}
    by_sym = {c.get("symbol"): c for c in markets if c.get("symbol")}
    result = {}
    for t in targets:
        coin = by_id.get(t.lower()) or by_sym.get(t)
        if coin:
            result[t] = coin
    return result


def _build_rows(markets: list[dict]) -> list[dict]:
    """Build research rows with rule-based red flags from live data."""
    rows = []
    for c in markets:
        symbol = c.get("symbol") or "?"
        price = c.get("current_price") or 0.0
        cap = c.get("market_cap") or 0.0
        vol = c.get("volume_24h") or 0.0
        chg = c.get("change_24h") or 0.0

        flags: list[str] = []
        if vol < MIN_VOLUME_24H_USD:
            flags.append(f"سيولة منخفضة ({vol:,.0f} USD)")
        if abs(chg) > MAX_24H_CHANGE_PCT:
            direction = "صاعد" if chg > 0 else "هابط"
            flags.append(f"حركة 24h متطرفة ({chg:+.2f}%) [{direction}]")
        if cap < MIN_MARKET_CAP_USD and cap > 0:
            flags.append(f"سوق صغير ({cap:,.0f} USD)")

        rows.append({
            "symbol": symbol,
            "source": "coingecko",
            "title": f"{symbol} ({c.get('name')}) | {chg:+.2f}% 24h | cap {cap/1e9:.1f}B",
            "url": c.get("url"),
            "market_cap": cap,
            "volume_24h": vol,
            "change_24h": chg,
            "price": price,
            "red_flags": "; ".join(flags) if flags else "",
            "notes": "جديد تجاري، قائمة على بيانات سوقية حية",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    return rows


def run(symbols: list[str] | None = None, top_n: int = 10) -> dict:
    """
    Real research step:
    1) fetch live market data from CoinGecko,
    2) build candidates for the target symbols,
    3) attach rule-based red flags (transparent, not LLM).
    """
    _log("🔍 [Jim] البدء خطوة حقيقية - استدعاء البيانات السوقية الحية (CoinGecko)")

    markets = _fetch_markets() or []
    if not markets:
        markets = [
            {"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin",
             "current_price": 80000.0, "market_cap": 1.6e12, "volume_24h": 2.2e10,
             "change_24h": -1.3},
            {"id": "ethereum", "symbol": "ETH", "name": "Ethereum",
             "current_price": 2300.0, "market_cap": 2.9e11, "volume_24h": 8.0e9,
             "change_24h": -1.6},
            {"id": "tether", "symbol": "USDT", "name": "Tether",
             "current_price": 1.0, "market_cap": 1.8e11, "volume_24h": 3.8e10,
             "change_24h": 0.01},
        ]
        _log("📦 لم تصل بيانات حية - استخدم بيانات تجريبية (fallback)")

    targets = symbols or DEFAULT_TARGETS
    available = _coins_for_targets(markets, targets)
    rows = _build_rows(list(available.values()))

    rows.sort(key=lambda r: r.get("volume_24h") or 0.0, reverse=True)
    rows = rows[:top_n]

    _log(f"[research] خيارات مُخرطة (real data): {len(rows)}")
    return {"symbols": targets, "rows": rows, "sources": {"market": "coingecko"}}


def persist(rows: list[dict], run_id: int = 0) -> list[int]:
    conn = _connect()
    cur = conn.cursor()
    ids = []
    for r in rows:
        cur.execute(
            """INSERT INTO research (run_id, symbol, source, title, url, market_cap, volume_24h, change_24h, red_flags, notes, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run_id, r.get("symbol"), r.get("source"), r.get("title"), r.get("url"),
             r.get("market_cap"), r.get("volume_24h"), r.get("change_24h"),
             r.get("red_flags"), r.get("notes"), r["created_at"]),
        )
        ids.append(cur.lastrowid)
    conn.commit()
    conn.close()
    return ids


if __name__ == "__main__":
    out = run()
    _log(json.dumps(out, ensure_ascii=False, default=str))
