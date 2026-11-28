#!/usr/bin/env python3
"""
self_heal.py — الوسيط العاجز لاستعادته (24/7)
==============================================
يقوم بفحص صحة الخدمات الأساسية، وإعادة تشغيل ما توقف (router :11435، mesh، web، cloud، sunna، integrations، kanban، homedock، jarvis، ollama) وكتابته تقرير.

الاستخدام
---------
    python self_heal.py --check       # فحص فوري (تشغيل + تقرير)
    python self_heal.py --daemon      # مراقبة مستمرة كل 5 دقائق (لا تنتهي)

مثال على تقرير
--------------
{
  "checked_at": "2026-10-16T02:20:00",
  "services": {"router": "up", "mesh": "up", "web": "up", ...},
  "restarts": [],
  "changed": false
}
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REPORT_FILE = DATA_DIR / "self_heal_report.json"


def _python() -> Path:
    """استخدم الـvenv الموجود فعلاً، ما تفترضش مستخدم محدد."""
    for candidate in (BASE_DIR / ".venv/Scripts/python.exe", Path(sys.executable)):
        if candidate.exists():
            return candidate
    return Path(sys.executable)


def _ollama() -> Path | None:
    """لا ننزّل ollama من مستودع مجهول؛ نكتشفو غير إلا كان مثبّتاً محلياً."""
    found = shutil.which("ollama")
    if found:
        return Path(found)
    for candidate in (
        Path("C:/Program Files/Ollama/ollama.exe"),
        Path("C:/Users/aether/AppData/Local/Programs/Ollama/ollama.exe"),
    ):
        if candidate.exists():
            return candidate
    return None

# الخدمات والمرافق (name -> (port, path))
SERVICES = {
    "router":    (11435, "health"),
    "mesh":      (11437, "health"),
    "web":       (5000, "health"),
    "cloud":     (5001, ""),
    "sunna":     (5100, "health"),
    "integrations": (5102, "health"),
    "kanban":    (5103, "health"),
    "homedock":  (5104, "health"),
    "jarvis":    (8000, "docs"),
    "ollama":    (11434, "api/tags"),
}

# طريقة إعادة التشغيل المفضلة: تشغيل مزامن بمساعدة PowerShell (Start-Process -WindowStyle Hidden)
def restart_service(name: str, port: int, path: str):
    """إعادة تشغيل خدمة مستقلة (مرة واحدة لكل خدمة)."""
    candidates = {
        "router":    ["src/ai_router.py"],
        "mesh":      ["src/agent_mesh.py"],
        "web":       ["src/web_interface.py"],
        "cloud":     ["src/cloud_desktop_agent.py"],
        "sunna":     ["src/sunna_api.py"],
        "integrations": ["src/integrations_api.py"],
        "kanban":    ["src/kanban_api.py"],
        "homedock":  ["src/homedock_dashboard.py"],
        "jarvis":    ["src/jarvis_api_minimal.py"],
    }
    log_out = DATA_DIR / "logs" / f"self_heal_{name}.out.log"
    log_err = DATA_DIR / "logs" / f"self_heal_{name}.err.log"
    log_out.parent.mkdir(parents=True, exist_ok=True)

    if name == "ollama":
        binary = _ollama()
        if binary is None:
            return "unavailable: ollama non installe localement"
        executable, argument, workdir = str(binary), "serve", str(binary.parent)
    else:
        script = next((BASE_DIR / s for s in candidates.get(name, ["src/app.py"])
                       if (BASE_DIR / s).exists()), None)
        if script is None:
            return f"unavailable: script introuvable pour {name}"
        executable, argument, workdir = str(_python()), str(script), str(BASE_DIR)

    command = (
        f"Start-Process -FilePath '{executable}' -ArgumentList '{argument}' "
        f"-WorkingDirectory '{workdir}' -WindowStyle Hidden "
        f"-RedirectStandardOutput '{log_out}' -RedirectStandardError '{log_err}'"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            capture_output=True, timeout=60, check=False,
        )
        if result.returncode != 0:
            return f"failed: {result.stderr.decode('utf-8', 'replace').strip()[:200]}"
        return True
    except Exception as e:
        return f"failed: {e}"

def check_service(port: int, path: str) -> str:
    """فحص خادم: 200 = up، غير ذلك = down"""
    import urllib.request
    import urllib.error
    url = f"http://127.0.0.1:{port}/{path}"
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return "up" if r.status == 200 else "down"
    except Exception:
        return "down"

def heal() -> dict:
    report = {
        "checked_at": datetime.now().isoformat(),
        "services": {},
        "restarts": [],
        "changed": False,
    }
    changed = False
    for name, (port, path) in SERVICES.items():
        status = check_service(port, path)
        report["services"][name] = status
        if status == "down":
            report["restarts"].append(f"{name}:down")
            res = restart_service(name, port, path)
            if res is True:
                time.sleep(2)
                new = check_service(port, path)
                report["services"][name] = new
                report["restarts"][-1] += f" -> {new}"
                if new == "up":
                    changed = True
            elif str(res).startswith("unavailable:"):
                report["services"][name] = "unavailable"
                report["restarts"][-1] += f" {res}"
                changed = False
            else:
                report["restarts"][-1] += f" FAIL: {res}"
                changed = True
    report["changed"] = changed
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="فحص + إعادة تشغيل (إظهار التقرير)")
    ap.add_argument("--daemon", action="store_true", help="المراقبة المستمرة (5 دقائق)")
    args = ap.parse_args()

    if args.daemon:
        print("🔧 self_heal daemon démarré (5 min). Ctrl+C لإنهاء.")
        try:
            while True:
                r = heal()
                print(f"[{r['checked_at']}] {'✓' if r['changed'] else '●'} {r['services']}")
                time.sleep(300)
        except KeyboardInterrupt:
            print("⏹️ إيقاف.")
        return

    # فحص واحد (وضع التقرير)
    report = heal()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\n📄 تقرير في {REPORT_FILE}")

if __name__ == "__main__":
    main()
