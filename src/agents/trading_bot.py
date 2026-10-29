#!/usr/bin/env python3
"""
🤖 Trading Bot — وكيل إدارة المحافظ
================================================================================

يقوم هاد الوكيل بإدارة المحافظ والمحافظ المالية
وتنفيذ الصفقات بناءً على تحليلات السوق.

المزايا:
  1. إدارة المحافظ
  2. تنفيذ الصفقات
  3. تتبع الأداء
  4. آليات الأمان
"""

import json
import os
import logging
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"
STATE_FILE = DATA_DIR / "trading_bot_state.json"
LOG_FILE = LOGS_DIR / "trading_bot.log"

# إعدادات التسجيل
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("trading_bot")


class TradingBot:
    """وكيل إدارة المحافظ والمحافظ"""

    def __init__(self):
        self.knowledge = {
            "portfolio": {
                "cards": [],
                "holdings": {},
                "cash": 10000.0,
                "total_value": 10000.0,
            },
            "trades": [],
            "performance": [],
            "notifications": [],
            "last_run": None,
            "status": "idle",
        }
        self._ensure_data_files()
        self._log("شبدأ وكيل التداول (Trading Bot)")

    def _ensure_data_files(self):
        """تأكد من وجود ملفات البيانات"""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        if not STATE_FILE.exists():
            with open(STATE_FILE, 'w') as f:
                json.dump(self.knowledge, f, indent=2, ensure_ascii=False)

    def _log(self, message):
        """سجل الرسالة"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_msg + "\n")

    def load_portfolio(self):
        """تحميل المحفظة"""
        self._log("📊 جارٍ تحميل المحفظة...")

        portfolio = self.knowledge["portfolio"]

        # بيانات تجريبية للمحفظة
        sample_assets = [
            {"symbol": "BTC", "name": "Bitcoin", "amount": 0.5, "price": 45000},
            {"symbol": "ETH", "name": "Ethereum", "amount": 2.0, "price": 3000},
            {"symbol": "USDT", "name": "Tether", "amount": 1000, "price": 1.0},
        ]

        for asset in sample_assets:
            total = asset["amount"] * asset["price"]
            portfolio["holdings"][asset["symbol"]] = {
                "symbol": asset["symbol"],
                "name": asset["name"],
                "amount": asset["amount"],
                "price": asset["price"],
                "total": total,
            }
            portfolio["total_value"] += total

        self._log(f"✅ حمّلت المحفظة بقيمة {portfolio['total_value']:.2f} درهم")
        return portfolio

    def analyze_signal(self, asset, trend, confidence):
        """
        تحليل إشارة التداول
        """
        self._log(f"📈 تحليل إشارة {asset}...")

        # بسيط (يتم استبدالها بلوحة تحكم أو نموذج ML)
        signal = "hold"
        action = "none"
        confidence_score = 0.5

        if trend == "📈 صعودي":
            if confidence > 0.7:
                signal = "buy"
                action = "buy"
                confidence_score = 0.8
            elif confidence > 0.5:
                signal = "hold"
                action = "hold"
                confidence_score = 0.6
            else:
                signal = "sell"
                action = "sell"
                confidence_score = 0.4
        elif trend == "📉 هابط":
            if confidence > 0.7:
                signal = "sell"
                action = "sell"
                confidence_score = 0.8
            elif confidence > 0.5:
                signal = "hold"
                action = "hold"
                confidence_score = 0.6
            else:
                signal = "buy"
                action = "buy"
                confidence_score = 0.4

        return {
            "asset": asset,
            "signal": signal,
            "action": action,
            "confidence": confidence_score,
            "timestamp": datetime.now().isoformat(),
        }

    def execute_trade(self, signal):
        """تنفيذ الصفقة"""
        self._log(f"🔄 تنفيذ الصفقة: {signal['action']} {signal['asset']}")

        trade = {
            **signal,
            "portfolio_value": self.knowledge["portfolio"]["total_value"],
            "cash": self.knowledge["portfolio"]["cash"],
            "timestamp": datetime.now().isoformat(),
        }
        self.knowledge["trades"].append(trade)

        # تحديث المحفظة (بساطة)
        self.knowledge["portfolio"]["total_value"] *= 1.01  # زيادة بسيطة
        self.knowledge["portfolio"]["cash"] = max(0, self.knowledge["portfolio"]["cash"] - 100)

        self._log(f"✅ تم تنفيذ الصفقة بنجاح")
        return trade

    def generate_trade_plan(self):
        """توليد خطة التداول"""
        self._log("🔮 جارٍ توليد خطة التداول...")

        portfolio = self.knowledge["portfolio"]
        plan = []

        # بيانات تجريبية (يتم استبدالها بالبيانات الحقيقية)
        market_data = [
            {"asset": "BTC", "trend": "📈 صعودي", "confidence": 0.85},
            {"asset": "ETH", "trend": "📈 صعودي", "confidence": 0.75},
            {"asset": "XRP", "trend": "📉 هابط", "confidence": 0.65},
            {"asset": "SOL", "trend": "📈 صعودي", "confidence": 0.70},
        ]

        for data in market_data:
            signal = self.analyze_signal(data["asset"], data["trend"], data["confidence"])
            if signal["action"] != "none":
                plan.append({
                    **signal,
                    "recommendation": f"شراء ({signal['action']}) عقد {signal['asset']} بسعر 10000",
                    "target_price": 11000,
                    "stop_loss": 9000,
                    "timestamp": datetime.now().isoformat(),
                })
                self.execute_trade(signal)

        self.knowledge["performance"].append({
            "timestamp": datetime.now().isoformat(),
            "portfolio_value": portfolio["total_value"],
            "trades_count": len(self.knowledge["trades"]),
        })

        self._log(f"✅ أنجز خطة التداول ({len(plan)} صفقات)")
        return plan

    def track_performance(self):
        """تتبع الأداء"""
        self._log("📊 جارٍ تتبع الأداء...")

        performance = self.knowledge["portfolio"]["total_value"]
        initial = 10000.0
        return {
            "current_value": performance,
            "initial_value": initial,
            "return_pct": round((performance - initial) / initial * 100, 2),
            "trades": len(self.knowledge["trades"]),
            "timestamp": datetime.now().isoformat(),
        }

    def generate_notification(self):
        """توليد الإشعارات"""
        notifications = []
        portfolio = self.knowledge["portfolio"]

        if portfolio["total_value"] > 10500:
            notifications.append({
                "type": "profit",
                "message": f"💰 ربح!: المحفظة تبلغ {portfolio['total_value']:.2f}",
                "timestamp": datetime.now().isoformat(),
            })
        elif portfolio["total_value"] < 9500:
            notifications.append({
                "type": "loss",
                "message": f"⚠️ خسارة: المحفظة تبلغ {portfolio['total_value']:.2f}",
                "timestamp": datetime.now().isoformat(),
            })

        self.knowledge["notifications"] = notifications
        self._log(f"📢 {len(notifications)} إشعار")
        return notifications

    def save_knowledge(self):
        """حفظ المعرفة"""
        self.knowledge["last_run"] = datetime.now().isoformat()
        with open(STATE_FILE, 'w') as f:
            json.dump(self.knowledge, f, indent=2, ensure_ascii=False)

    def run(self):
        """تنفيذ الوكيل بالكامل"""
        self._log("=" * 60)
        self._log("🤖 وكيل التداول - Trading Bot")
        self._log("=" * 60)
        self._log("")

        # 1. تحميل المحفظة
        self.load_portfolio()

        # 2. خطة التداول
        plan = self.generate_trade_plan()

        # 3. الأداء
        performance = self.track_performance()
        self._log(f"📈 القيمة الحالية: {performance['current_value']:.2f}")
        self._log(f"📈 العائد: {performance['return_pct']:.2f}%")
        self._log(f"📈 الصفقات: {performance['trades']}")

        # 4. الإشعارات
        notifications = self.generate_notification()

        # 5. الحفظ
        self.save_knowledge()

        # 6. الملخص
        self._log("")
        self._log("=" * 60)
        self._log("✅ النتائج:")
        for trade in plan[:5]:
            self._log(f"  {trade['asset']}: {trade['action']} • موثوقية: {trade['confidence']:.2f}")
        self._log(f"")
        self._log(f"📊 إجمالي الصفقات: {len(plan)}")
        self._log(f"📢 الإشعارات: {len(notifications)}")
        self._log(f"⏰ آخر تحديث: {self.knowledge['last_run']}")
        self._log("=" * 60)
        self._log("✅ وكيل التداول مكتمل!")


if __name__ == "__main__":
    bot = TradingBot()
    bot.run()
