#!/usr/bin/env python3
"""
Security Agent — وكيل الأمان والإشراف
=====================================================
يقوم ب:
- مراقبة الأنشطة الأمنية
- كشف الخلفيات
- فحص السيرفر والخدمات
- إدارة التسجيلات والشكاوى
- تنفيذ إجراءات الأمان
"""

import hashlib
import json
import os
import subprocess
import socket
from datetime import datetime
from pathlib import Path

# Base directory for the project
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
BASE_DIR = PROJECT_DIR  # data/logs is under project root, not src/data

# Data files
STATE_FILE = BASE_DIR / "data" / "security_agent_state.json"
LOG_FILE = BASE_DIR / "data" / "logs" / "security_agent.log"

# Security rules
SECURITY_RULES = {
    "monitor_port": {"ports": [22, 80, 443, 5000, 5001, 5100, 5103, 5105, 11435, 11436, 11437], "description": "منافذ الخدمات الرئيسية"},
    "monitor_process": {"processes": ["python", "java", "node", "socat", "ngrok"], "description": "عمليات الخدمات الرئيسية"},
    "allowed_ips": {"description": "السيرفرات والخوادم المسموح بالوصول"},
}


class SecurityAgent:
    """وكيل الأمان والمراقبة"""

    def __init__(self):
        self.state = {
            "alerts": [],
            "violations": [],
            "checked_ports": [],
            "checked_processes": [],
            "security_events": [],
            "last_check": None
        }
        self._ensure_state_file()
        self._log("شstarted وكيل الأمان (Security Agent)")

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

    def check_services(self):
        """فحص الخدمات الجارية"""
        services = {
            "5000": "JARVIS Web",
            "5001": "Cloud Desktop",
            "5100": "Sunna API",
            "5103": "Kanban Board",
            "5103": "Kanban Board",
            "5105": "Sunna Dashboard",
            "11435": "AI Router",
            "11436": "Orchestrator",
            "11437": "Agent Mesh"
        }

        results = {}
        for port, name in services.items():
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                results[port] = {"healthy": result == 0, "name": name, "port": port}
            except Exception as e:
                results[port] = {"healthy": False, "name": name, "port": port, "error": str(e)}

        # Check for anomalies
        for port, info in results.items():
            if not info["healthy"]:
                self.state["alerts"].append({
                    "type": "service_down",
                    "port": port,
                    "name": info["name"],
                    "timestamp": datetime.now().isoformat()
                })
        self.state["checked_ports"] = results
        return results

    def check_processes(self):
        """فحص العمليات الجارية"""
        processes = [
            "python", "java", "node", "socat", "ngrok",
            "flask", "uvicorn", "gunicorn"
        ]
        running_processes = []
        for proc in processes:
            try:
                # Check if process is running
                import subprocess
                result = subprocess.run(
                    ["tasklist" if os.name == "nt" else "ps", "-ef"],
                    capture_output=True, text=True, timeout=5
                )
                if proc.lower() in result.stdout.lower():
                    running_processes.append(proc)
            except Exception as e:
                pass

        self.state["running_processes"] = running_processes
        return running_processes

    def check_network(self):
        """فحص الشبكة"""
        try:
            import socket
            # Check public IP
            ip = socket.gethostbyname(socket.gethostname())
            # Check default gateway
            gateway = None
            try:
                with open("/proc/net/route") as f:
                    for line in f:
                        if line.split()[0] != "Iface":
                            parts = line.split()
                            if parts[1] == "00000000":
                                gateway = parts[2]
                                break
            except Exception:
                pass

            return {
                "hostname": socket.gethostname(),
                "ip": ip,
                "gateway": gateway,
                "local": True
            }
        except Exception as e:
            return {"error": str(e)}

    def scan_files(self, directory="data/"):
        """فحص الملفات الحساسة"""
        sensitive_patterns = ["password", "password.txt", ".env", "key", "secret", "token"]
        found_files = []

        for root, dirs, files in os.walk(directory):
            for file in files:
                for pattern in sensitive_patterns:
                    if pattern.lower() in file.lower():
                        found_files.append(os.path.join(root, file))
                        break

        self.state["found_files"] = found_files
        return found_files

    def check_firewall(self):
        """فحص جدران الحماية"""
        try:
            # Check if firewall is active
            if os.name == "nt":
                # Windows
                result = subprocess.run(["netsh", "firewall", "show", "state"], capture_output=True, text=True, timeout=5)
                return {"firewall_status": "Windows" if result.returncode == 0 else "Unknown"}
            else:
                # Linux
                result = subprocess.run(["iptables", "-L", "-n"], capture_output=True, text=True, timeout=5)
                return {"firewall_status": "Active" if result.returncode == 0 else "Disabled"}
        except Exception:
            return {"firewall_status": "Unknown"}

    def generate_report(self):
        """توليد تقرير الأمان"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "alerts": self.state["alerts"],
            "violations": self.state["violations"],
            "checked_ports": self.state["checked_ports"],
            "checked_processes": self.state["checked_processes"],
            "network_info": self.check_network(),
            "firewall_status": self.check_firewall(),
            "found_files": self.scan_files(),
            "security_events": self.state["security_events"]
        }

        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

        self._log("تقرير الأمان تم توليده بنجاح")
        return report

    def run(self):
        """تشغيل الوسيط"""
        self._log("شstarted وكيل الأمان (Security Agent)")
        self.check_services()
        self.check_processes()
        self.check_network()
        self.check_firewall()
        self.generate_report()
        self._log("انتهى وكيل الأمان")


if __name__ == "__main__":
    agent = SecurityAgent()
    agent.run()
