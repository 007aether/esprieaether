#!/usr/bin/env python3
"""
Daily Report Agent — التقرير اليومي الآلي
=====================================================
يولّد تقرير يومي تلقائي للنظام والشركة
- ملخص الخدمات
- مؤشرات الأداء
- التطورات الهامة
- التوصيات
"""

import json
import os
from datetime import datetime
from pathlib import Path

# Base directory for the project
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
BASE_DIR = PROJECT_DIR  # data/logs is under project root, not src/data

# Data files
STATE_FILE = BASE_DIR / "data" / "daily_report_state.json"
LOG_FILE = BASE_DIR / "data" / "logs" / "daily_report.log"

class DailyReport:
    """وكيل التقرير اليومي"""

    def __init__(self):
        self.state = {
            "last_report": None,
            "reports_generated": 0,
            "reports": []
        }
        self._ensure_state_file()
        self._log("شstarted وكيل التقرير اليومي (Daily Report)")

    def _ensure_state_file(self):
        """تأكد من وجود ملف الحالة"""
        import os
        os.makedirs(STATE_FILE.parent, exist_ok=True)
        if not STATE_FILE.exists():
            with open(STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)

    def _log(self, message):
        """سجل الرسالة"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        with open(LOG_FILE, 'a') as f:
            f.write(log_msg + "\n")

    def get_service_status(self):
        """استرجاع حالة الخدمات"""
        services = {
            "JARVIS Web (5000)": self._check_port(5000),
            "Cloud Desktop (5001)": self._check_port(5001),
            "Sunna API (5100)": self._check_port(5100),
            "Kanban Board (5103)": self._check_port(5103),
            "Sunna Dashboard (5105)": self._check_port(5105),
            "AI Router (11435)": self._check_port(11435),
            "Orchestrator (11436)": self._check_port(11436),
            "Agent Mesh (11437)": self._check_port(11437),
            "Cloud Desktop (5173)": self._check_port(5173),
        }
        return services

    def _check_port(self, port):
        """فحص منفذ معين"""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return {"port": port, "healthy": result == 0}

    def check_system_health(self):
        """فحص حالة النظام"""
        return {
            "timestamp": datetime.now().isoformat(),
            "services": self.get_service_status(),
            "total_services": 9,
            "healthy_services": sum(1 for s in self.get_service_status().values() if s["healthy"]),
            "down_services": sum(1 for s in self.get_service_status().values() if not s["healthy"])
        }

    def generate_report(self, date=None):
        """توليد تقرير يومي"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        system_status = self.check_system_health()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = {
            "date": date,
            "timestamp": timestamp,
            "system_status": system_status,
            "services": {
                "healthy": sum(1 for s in system_status["services"].values() if s["healthy"]),
                "down": sum(1 for s in system_status["services"].values() if not s["healthy"]),
                "total": system_status["services"]
            },
            "summary": self._generate_summary(),
            "recommendations": self._generate_recommendations()
        }

        # Save report
        self.state["reports"].insert(0, report)
        if len(self.state["reports"]) > 30:  # Keep last 30 reports
            self.state["reports"] = self.state["reports"][:30]

        self.state["last_report"] = report
        self.state["reports_generated"] += 1

        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

        self._log(f"📊 التقرير اليومي مُولّد: {date}")
        return report

    def _generate_summary(self):
        """توليد ملخص مبسط"""
        services = self.get_service_status()
        healthy = sum(1 for s in services.values() if s["healthy"])
        total = len(services)
        return f"النظام يعمل بعمال: {healthy}/{total} ({healthy/total*100:.1f}%)"

    def _generate_recommendations(self):
        """توليد التوصيات"""
        services = self.get_service_status()
        recommendations = []

        for name, info in services.items():
            if not info["healthy"]:
                recommendations.append(f"🔴 {name}: خدمة متوقفة - يرجى التحقق")

        if recommendations:
            recommendations.append("📋 مراجعة سريعة للمهارات المطلوبة")
        else:
            recommendations.append("✅ كل الخدمات تعمل بشكل سليم")

        return recommendations

    def run(self, date=None):
        """تشغيل التقرير"""
        self._log("شstarted التقرير اليومي (Daily Report)")
        report = self.generate_report(date)
        self._log(f"📊 تقرير اليوم مُولّد: {report['date']}")
        return report


if __name__ == "__main__":
    report = DailyReport()
    report.run()
