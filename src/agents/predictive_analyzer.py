#!/usr/bin/env python3
"""
🔮 Predictive Analyzer — وكيل تحليل اتجاهات السوق
================================================================================

يقوم هذا الوكيل بتحليل اتجاهات السوق (العملات المشفرة، الأسهم، الفواتير)
وتوقعات المستقبل بناءً على البيانات التاريخية.

المزايا:
  1. تحليل الاتجاهات (صعود/هبوط)
  2. تنبؤات المستقبل
  3. تقييم المخاطر
  4. إشعارات الفرص
"""

import json
import os
import logging
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"
STATE_FILE = DATA_DIR / "predictive_analyzer_state.json"
LOG_FILE = LOGS_DIR / "predictive_analyzer.log"

# إعدادات التسجيل
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("predictive_analyzer")


class PredictiveAnalyzer:
    """وكيل تحليل اتجاهات السوق"""

    def __init__(self):
        self.knowledge = {
            "market_data": [],
            "trend_analysis": [],
            "predictions": [],
            "notifications": [],
            "last_run": None,
            "status": "idle",
        }
        self._ensure_data_files()
        self._log("شبدأ وكيل التحليل التنبؤي")

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

    def fetch_market_data(self, assets=None):
        """
        حصول البيانات من مصادر السوق
        (في الإنتاج: يالرجال من APIs الفعلية)
        """
        self._log("📈 جارٍ حصول البيانات من السوق...")

        # بيانات تجريبية (في الإنتاج: يالرجال من APIs الفعلية)
        default_assets = assets or ["BTC", "ETH", "XRP", "SOL", "DOGE", "ADA"]

        sample_data = []
        for asset in default_assets:
            import time
            sample_data.append({
                "asset": asset,
                "price": round(100 + len(asset) * 10 + time.time() % 50, 2),
                "change_24h": round(1.5 + (time.time() % 5), 2),
                "volume_24h": round(100000 + len(asset) * 1000, 0),
                "timestamp": datetime.now().isoformat(),
            })

        self.knowledge["market_data"] = sample_data
        self._log(f"✅ حصلت على بيانات {len(sample_data)} أصل")
        return sample_data

    def analyze_trends(self, data=None):
        """تحليل الاتجاهات"""
        self._log("📊 جارٍ تحليل الاتجاهات...")

        data = data or self.knowledge["market_data"]

        trends = []
        for item in data:
            change = item.get("change_24h", 0)
            trend = "صعودي 📈" if change > 0 else "هابط 📉"
            volatility = abs(change) / 10

            trend_info = {
                "asset": item["asset"],
                "price": item["price"],
                "change_24h": change,
                "trend": trend,
                "volatility": volatility,
                "confidence": min(abs(change) / 5 + 0.5, 1.0),
                "timestamp": datetime.now().isoformat(),
            }
            trends.append(trend_info)

        self.knowledge["trend_analysis"] = trends
        self._log(f"✅ أنجز التحليل على {len(trends)} أصل")
        return trends

    def predict_future(self, data=None):
        """التوقعات المستقبلية"""
        self._log("🔮 جارٍ إجراء التنبؤات...")

        data = data or self.knowledge["trend_analysis"]

        predictions = []
        for item in data:
            change = item["change_24h"]
            confidence = item["confidence"]
            direction = "صعودي" if change > 0 else "هابط"

            # توقع مبسط
            predicted_move = change * 1.5
            recommendation = self._generate_recommendation(change, confidence)

            prediction = {
                "asset": item["asset"],
                "direction": direction,
                "predicted_move": round(predicted_move, 2),
                "confidence": round(confidence, 2),
                "recommendation": recommendation,
                "risk_level": self._assess_risk(change, confidence),
                "timestamp": datetime.now().isoformat(),
            }
            predictions.append(prediction)

        self.knowledge["predictions"] = predictions
        self._log(f"✅ أنجز التنبؤات على {len(predictions)} أصل")
        return predictions

    def _generate_recommendation(self, change, confidence):
        """توليد التوصية"""
        if confidence > 0.7:
            if change > 0:
                return "🔼 شراء (Buy) - يوجد اتجاه صعودي قوي"
            else:
                return "🔻 بيع (Sell) - يوجد اتجاه هابط قوي"
        elif confidence > 0.5:
            return "🟡 الاحتفاظ (Hold) - مشاعر محايدة"
        else:
            return "🟢 تجنب (Avoid) - مخاطر عالية"

    def _assess_risk(self, change, confidence):
        """تقييم المستوى النسبي"""
        if confidence > 0.7 and abs(change) > 5:
            return "🟠 عالية"
        elif confidence > 0.5:
            return "🟡 متوسطة"
        else:
            return "🟢 منخفضة"

    def generate_notification(self, predictions):
        """توليد الإشعارات"""
        notifications = []
        for pred in predictions:
            if pred["risk_level"] == "🟠 عالية":
                notifications.append({
                    "type": "risk_alert",
                    "asset": pred["asset"],
                    "message": f"⚠️ {pred['asset']}: مستوى مخاطر عالية ({pred['risk_level']})",
                    "timestamp": pred["timestamp"],
                })
            elif "buy" in pred["recommendation"] and pred["confidence"] > 0.7:
                notifications.append({
                    "type": "buy_signal",
                    "asset": pred["asset"],
                    "message": f"🔼 {pred['asset']}: إشارة لشراء قوية",
                    "timestamp": pred["timestamp"],
                })

        self.knowledge["notifications"] = notifications
        self._log(f"📢 {len(notifications)} إشعار تم توليده")
        return notifications

    def save_knowledge(self):
        """حفظ المعرفة"""
        self.knowledge["last_run"] = datetime.now().isoformat()
        with open(STATE_FILE, 'w') as f:
            json.dump(self.knowledge, f, indent=2, ensure_ascii=False)

    def run(self):
        """تنفيذ الوكيل بالكامل"""
        self._log("=" * 60)
        self._log("🔮 وكيل التحليل التنبؤي - Predictive Analyzer")
        self._log("=" * 60)
        self._log("")

        # 1. حصول البيانات
        data = self.fetch_market_data()

        # 2. التحليل
        trends = self.analyze_trends(data)

        # 3. التنبؤات
        predictions = self.predict_future(trends)

        # 4. الإشعارات
        notifications = self.generate_notification(predictions)

        # 5. الحفظ
        self.save_knowledge()

        # 6. الملخص
        self._log("")
        self._log("=" * 60)
        self._log("✅ النتائج:")
        for pred in predictions:
            self._log(f"  {pred['asset']}: {pred['direction']} • موثوقية: {pred['confidence']:.2f} • {pred['risk_level']}")
        self._log(f"")
        self._log(f"📊 إجمالي التنبؤات: {len(predictions)}")
        self._log(f"📢 الإشعارات: {len(notifications)}")
        self._log(f"⏰ آخر تحديث: {self.knowledge['last_run']}")
        self._log("=" * 60)
        self._log("✅ وكيل التحليل التنبؤي مكتمل!")


if __name__ == "__main__":
    analyzer = PredictiveAnalyzer()
    analyzer.run()
