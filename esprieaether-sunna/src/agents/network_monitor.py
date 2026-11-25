#!/usr/bin/env python3
"""
Network Monitor Agent — وكيل مراقبة الشبكة
=====================================================
يقوم ب:
- فحص اتصال كل الأجهزة على الشبكة
- مراقبة DNS
- قياس سرعة الإنترنت
- كشف مشاكل الشبكة
- توليد تقرير دوري
"""

import socket
import psutil
import time
import json
from datetime import datetime
from pathlib import Path

# Base directory for the project
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
BASE_DIR = PROJECT_DIR  # data/logs is under project root, not src/data

# Default network interfaces to monitor
MONITORED_INTERFACES = ["eth0", "wlan0", "lo"]

# Data files
STATE_FILE = BASE_DIR / "data" / "network_monitor_state.json"
LOG_FILE = BASE_DIR / "data" / "logs" / "network_monitor.log"

class NetworkMonitor:
    """وكيل مراقبة الشبكة"""

    def __init__(self):
        self.state = {
            "last_check": None,
            "devices_online": 0,
            "devices_offline": 0,
            "dns_healthy": True,
            "internet_healthy": True,
            "bandwidth_used": 0,
            "errors": [],
            "last_report": {}
        }
        self._ensure_state_file()
        self._log("ش Uruguaysي برنامج المراقبة")

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

    def check_dns(self, dns_servers=["8.8.8.8", "1.1.1.1"]):
        """فحص DNS"""
        results = {}
        for dns in dns_servers:
            try:
                socket.gethostbyaddr(dns)
                results[dns] = {"healthy": True, "message": "DNS صحيح"}
            except Exception as e:
                results[dns] = {"healthy": False, "message": str(e)}
        self.state["dns_healthy"] = all(v["healthy"] for v in results.values())
        return results

    def check_internet(self, hosts=["google.com", "github.com", "youtube.com"]):
        """فحص اتصال الإنترنت"""
        results = {}
        for host in hosts:
            try:
                socket.create_connection((host, 80), timeout=5)
                results[host] = {"healthy": True, "message": "متصل"}
            except Exception as e:
                results[host] = {"healthy": False, "message": str(e)}
        self.state["internet_healthy"] = all(v["healthy"] for v in results.values())
        return results

    def get_bandwidth(self):
        """قياس استهلاك النطاق الترددي"""
        try:
            import psutil
            net = psutil.net_io_counters()
            return {
                "bytes_sent": net.bytes_sent,
                "bytes_recv": net.bytes_recv,
                "packets_sent": net.packets_sent,
                "packets_recv": net.packets_recv
            }
        except Exception as e:
            return {"error": str(e)}

    def get_interfaces(self):
        """حصول على واجهات الشبكة"""
        interfaces = []
        try:
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        interfaces.append({
                            "name": interface,
                            "ip": addr.address,
                            "netmask": addr.netmask,
                            "is_loopback": addr.address.startswith("127.")
                        })
                        break  # Only get first iteration for now
        except Exception as e:
            pass
        return interfaces

    def check_local_devices(self):
        """فحص الأجهزة المحلية على الشبكة"""
        devices = []
        try:
            # This is a simple scan - in production you'd use more advanced methods
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                        devices.append({
                            "ip": addr.address,
                            "interface": interface,
                            "type": "local_device"
                        })
        except Exception as e:
            self.state["errors"].append(f"Error checking local devices: {str(e)}")
        return devices

    def generate_report(self):
        """توليد تقرير شامل"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "dns_healthy": self.state["dns_healthy"],
            "internet_healthy": self.state["internet_healthy"],
            "bandwidth": self.get_bandwidth(),
            "interfaces": self.get_interfaces(),
            "errors": self.state["errors"]
        }

        # Save state
        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

        self._log("تقرير الشبكة تم توليده بنجاح")
        return report

    def run(self):
        """تشغيل الوسيط"""
        self._log("شبدأ رسم الوسيط (Network Monitor)")
        self.check_dns()
        self.check_internet()
        self.check_local_devices()
        self.generate_report()
        self._log("انتهى رسم الوسيط")


if __name__ == "__main__":
    monitor = NetworkMonitor()
    monitor.run()
