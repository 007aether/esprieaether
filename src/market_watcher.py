# Copyright (c) 2026 EsprieAmine / EsprieAether
# All rights reserved.
# ESPRIE AETHER V8 — Autonomous AI System

"""
⚡ EsprieAether - Market Watcher
مراقبة أسعار العملات + فرص
"""
import os
import json
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path.home() / "AETHER_V8"
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("market_watcher")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

MARKET_STATE = BASE_DIR / "market_state.json"

# ─── العملات للمتابعة ───
COINS = [
    "BTC", "ETH", "SOL", "BNB", "XRP",
    "ADA", "DOT", "MATIC", "AVAX", "LINK",
    "UNI", "ATOM", "ALGO", "NEAR",
]


class MarketWatcher:
    """مراقب السوق"""

    def __init__(self):
        self.state = self._load_state()

    def _load_state(self) -> dict:
        if MARKET_STATE.exists():
            try:
                return json.loads(MARKET_STATE.read_text())
            except Exception:
                pass
        return {
            "prices": {},
            "history": {},
            "alerts": [],
        }

    def _save_state(self):
        MARKET_STATE.write_text(
            json.dumps(self.state, indent=2, ensure_ascii=False)
        )

    # ─────────────────────────────────────
    #  جلب الأسعار
    # ─────────────────────────────────────
    def fetch_prices(self) -> dict:
        """جلب أسعار من CoinGecko"""
        try:
            # استخدم CoinGecko API المجاني
            ids = ",".join([
                "bitcoin", "ethereum", "solana", "binancecoin", "ripple",
                "cardano", "polkadot", "matic-network", "avalanche-2",
                "chainlink", "uniswap", "cosmos", "algorand", "near"
            ])

            r = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={
                    "ids": ids,
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_24hr_vol": "true",
                },
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()

            prices = {}
            for name, info in data.items():
                prices[name] = {
                    "usd": info.get("usd", 0),
                    "change_24h": info.get("usd_24h_change") or 0,
                    "volume_24h": info.get("usd_24h_vol", 0),
                }

            # احفظ
            self.state["prices"] = prices
            self.state["last_fetch"] = datetime.now().isoformat()

            # احفظ التاريخ
            today = datetime.now().date().isoformat()
            if "history" not in self.state:
                self.state["history"] = {}
            if today not in self.state["history"]:
                self.state["history"][today] = {}
            for name, info in prices.items():
                self.state["history"][today][name] = info["usd"]

            # احتفظ بـ 7 أيام فقط
            keys = sorted(self.state["history"].keys())
            if len(keys) > 7:
                for k in keys[:-7]:
                    del self.state["history"][k]

            self._save_state()
            logger.info(f"✅ تم جلب {len(prices)} عملة")
            return prices

        except Exception as e:
            logger.error(f"❌ فشل جلب الأسعار: {e}")
            return {}

    # ─────────────────────────────────────
    #  كشف الفرص
    # ─────────────────────────────────────
    def find_opportunities(self) -> list:
        """اكتشاف الفرص"""
        opportunities = []
        prices = self.state.get("prices", {})

        for name, info in prices.items():
            change = info.get("change_24h") or 0

            # فرصة 1: انخفاض كبير (فرصة شراء)
            if change <= -10:
                opportunities.append({
                    "type": "buy",
                    "coin": name,
                    "price": info["usd"],
                    "change": round(change, 2),
                    "message": f"{name} انخفض {round(change, 1)}% — فرصة شراء محتملة",
                })

            # فرصة 2: ارتفاع كبير (تنبيه بيع)
            elif change >= 15:
                opportunities.append({
                    "type": "sell",
                    "coin": name,
                    "price": info["usd"],
                    "change": round(change, 2),
                    "message": f"{name} ارتفع {round(change, 1)}% — فرصة بيع محتملة",
                })

        return opportunities

    # ─────────────────────────────────────
    #  تقرير
    # ─────────────────────────────────────
    def get_top_movers(self, limit: int = 5) -> list:
        """أعلى التحركات"""
        prices = self.state.get("prices", {})
        sorted_coins = sorted(
            prices.items(),
            key=lambda x: abs(x[1].get("change_24h") or 0),
            reverse=True,
        )
        return [
            {
                "coin": name,
                "price": info["usd"],
                "change": round(info.get("change_24h") or 0, 2),
            }
            for name, info in sorted_coins[:limit]
        ]

    def format_telegram(self) -> str:
        """تنسيق للـ Telegram"""
        prices = self.state.get("prices", {})

        if not prices:
            return "📊 لا توجد بيانات. شغّل `/market` أولاً."

        text = "📊 *Market Watcher*" + chr(10)
        text += "_" + self.state.get("last_fetch", "")[:19] + "_" + chr(10) + chr(10)

        # أعلى 5
        movers = self.get_top_movers(5)
        text += "*أعلى التحركات:*" + chr(10)
        for m in movers:
            arrow = "🟢" if m["change"] > 0 else "🔴"
            text += f"{arrow} `{m['coin']}`: `${m['price']:,.2f}` ({m['change']:+.1f}%)" + chr(10)

        # فرص
        opps = self.find_opportunities()
        if opps:
            text += chr(10) + "*🎯 فرص:*" + chr(10)
            for o in opps[:3]:
                emoji = "🟢" if o["type"] == "buy" else "🔴"
                text += f"{emoji} {o['message']}" + chr(10)

        return text


if __name__ == "__main__":
    print("═" * 60)
    print("📊 Market Watcher Test")
    print("═" * 60)

    m = MarketWatcher()

    # جلب
    print("\n▶ جلب الأسعار...")
    prices = m.fetch_prices()
    print(f"  عدد: {len(prices)}")

    # أعلى التحركات
    print("\n▶ أعلى التحركات:")
    for mover in m.get_top_movers(5):
        arrow = "🟢" if mover["change"] > 0 else "🔴"
        print(f"  {arrow} {mover['coin']}: ${mover['price']:,.2f} ({mover['change']:+.1f}%)")

    # فرص
    print("\n▶ الفرص:")
    opps = m.find_opportunities()
    if opps:
        for o in opps:
            print(f"  • {o['message']}")
    else:
        print("  لا فرص حالياً")

    print("\n▶ التقرير:")
    print(m.format_telegram())
