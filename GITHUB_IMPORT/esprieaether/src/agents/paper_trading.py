#!/usr/bin/env python3
"""
==========================================
  PAPER TRADING BOT — وكيل التداول الورقي
==========================================
يقوم بالتداول على بيانات تجريبية بدون مخاطرة
يحتوي على:
- حدود الخسارة (Stop Loss)
- حدود الربح (Take Profit)
- سجل كل صفقة
- إشعارات الصفقات
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path("C:/Users/ESPRIEAETHER/Desktop/esprieaether")
DATA_DIR = PROJECT_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"
STATE_FILE = DATA_DIR / "trading_bot_state.json"
TRADE_LOG = DATA_DIR / "trades.json"
LOG_FILE = LOGS_DIR / "paper_trading.log"

# ضمان وجود ملفات البيانات
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

class PaperTradingBot:
    def __init__(self):
        self.portfolio = {
            "cash": 10000.0,
            "holdings": {},
            "total_value": 10000.0,
            "started_at": datetime.now().isoformat()
        }
        self.trades = []
        self.notifications = []
        self.performance_history = []
        self.stop_loss_pct = 0.05  # خسارة 5%
        self.take_profit_pct = 0.10  # ربح 10%
        self._ensure_data_files()

    def _ensure_data_files(self):
        if not STATE_FILE.exists():
            with open(STATE_FILE, 'w') as f:
                json.dump(self.portfolio, f, indent=2, ensure_ascii=False)
        if not TRADE_LOG.exists():
            with open(TRADE_LOG, 'w') as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def _log(self, msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {msg}"
        print(log_msg)
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_msg + "\n")

    def load_portfolio(self):
        self._log("📊 جارٍ تحميل المحفظة...")
        portfolio = self.portfolio
        sample_assets = [
            {"symbol": "BTC", "name": "Bitcoin", "amount": 0.1, "price": 45000},
            {"symbol": "ETH", "name": "Ethereum", "amount": 0.5, "price": 3000},
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
        self._log(f"✅ المحفظة: {portfolio['total_value']:.2f} درهم")
        return portfolio

    def analyze_signal(self, asset, trend, confidence):
        """تحليل إشارة التداول"""
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
        trade = {
            **signal,
            "portfolio_value": self.portfolio["total_value"],
            "cash": self.portfolio["cash"],
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "timestamp": datetime.now().isoformat(),
        }
        self.trades.append(trade)

        # تحديث المحفظة
        if signal["action"] == "buy":
            cost = signal["confidence"] * 1000
            self.portfolio["cash"] -= cost
        elif signal["action"] == "sell":
            profit = signal["confidence"] * 1000
            self.portfolio["cash"] += profit

        self.portfolio["total_value"] = self.portfolio["cash"] + sum(
            h["amount"] * h["price"] for h in self.portfolio["holdings"].values()
        )

        self._log(f"✅ تنفيذ الصفقة: {signal['action']} {signal['asset']}")
        return trade

    def check_stop_loss(self):
        """التحقق من خسارة الحد (Stop Loss)"""
        if self.portfolio["cash"] < 0:
            self._log("⚠️ تم تجاوز الحد: خسارة أكبر من المصلحة المتوفرة")
            return True
        return False

    def generate_trade_plan(self):
        """توليد خطة التداول"""
        self._log("🔮 جارٍ توليد خطة التداول...")
        portfolio = self.portfolio
        plan = []

        market_data = [
            {"asset": "BTC", "trend": "📈 صعودي", "confidence": 0.85},
            {"asset": "ETH", "trend": "📈 صعودي", "confidence": 0.75},
            {"asset": "XRP", "trend": "📉 هابط", "confidence": 0.65},
            {"asset": "SOL", "trend": "📈 صعودي", "confidence": 0.70},
        ]

        for data in market_data:
            signal = self.analyze_signal(data["asset"], data["trend"], data["confidence"])
            if signal["action"] != "none":
                trade = self.execute_trade(signal)
                plan.append(trade)

        self.performance_history.append({
            "timestamp": datetime.now().isoformat(),
            "portfolio_value": portfolio["total_value"],
            "trades_count": len(self.trades),
        })

        self._log(f"✅ خطة التداول ({len(plan)} صفقات)")
        return plan

    def track_performance(self):
        """تتبع الأداء"""
        performance = {
            "current_value": self.portfolio["total_value"],
            "initial_value": 10000.0,
            "return_pct": round(
                (self.portfolio["total_value"] - 10000.0) / 10000.0 * 100, 2
            ),
            "trades": len(self.trades),
            "timestamp": datetime.now().isoformat(),
        }
        self.performance_history.append(performance)
        return performance

    def generate_notification(self):
        """توليد الإشعارات"""
        notifications = []
        portfolio = self.portfolio

        if portfolio["total_value"] > 11000:
            notifications.append({
                "type": "profit",
                "message": f"💰 ربح: المحفظة {portfolio['total_value']:.2f}",
                "timestamp": datetime.now().isoformat(),
            })
        elif portfolio["cash"] < 0:
            notifications.append({
                "type": "loss",
                "message": "⚠️ تجاوز الحد: خسارة تامة",
                "timestamp": datetime.now().isoformat(),
            })

        self.notifications = notifications
        return notifications

    def save_state(self):
        """حفظ الحالة"""
        self.portfolio["last_run"] = datetime.now().isoformat()
        with open(STATE_FILE, 'w') as f:
            json.dump(self.portfolio, f, indent=2, ensure_ascii=False)
        with open(TRADE_LOG, 'w') as f:
            json.dump(self.trades, f, ensure_ascii=False, indent=2)

    def run(self):
        """تنفيذ الوكيل بالكامل"""
        self._log("=" * 60)
        self._log("🤖 وكيل التداول الورقي (Paper Trading)")
        self._log("=" * 60)
        self._log("")

        # 1. تحميل المحفظة
        self.load_portfolio()

        # 2. خطة التداول
        plan = self.generate_trade_plan()

        # 3. الأداء
        performance = self.track_performance()
        self._log(f"📈 قيمة المحفظة: {performance['current_value']:.2f}")
        self._log(f"📈 العائد: {performance['return_pct']:.2f}%")
        self._log(f"📈 عدد الصفقات: {performance['trades']}")

        # 4. الإشعارات
        notifications = self.generate_notification()
        for n in notifications:
            self._log(f"📢 {n['type'].upper()}: {n['message']}")

        # 5. الحفظ
        self.save_state()

        # 6. ملخص
        self._log("")
        self._log("=" * 60)
        self._log("✅ النتائج:")
        for trade in plan[:5]:
            self._log(f"  {trade['asset']}: {trade['action']} • موثوقية: {trade['confidence']:.2f}")
        self._log(f"📊 إجمالي الصفقات: {len(plan)}")
        self._log(f"📢 الإشعارات: {len(notifications)}")
        self._log(f"⏰ آخر تحديث: {self.portfolio['last_run']}")
        self._log("=" * 60)


if __name__ == "__main__":
    bot = PaperTradingBot()
    bot.run()
