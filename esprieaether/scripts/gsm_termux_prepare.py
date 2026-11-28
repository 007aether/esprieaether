"""J199 — يحضّر حزمة Termux/APK للـGSM بلا أي تنفيذ وبلا لمس touping.exe.

السكريبت كيكتب ملفات نصية قابلة للمراجعة فقط:
  - gsm_termux_plan/worker.py   : عامل قراءة فقط داخل Termux
  - gsm_termux_plan/bootstrap.sh: أوامر تحضير داخل Termux (نص، ما كيتنفّذش)
  - gsm_termux_plan/plan.json   : حالة كل جهاز = pending، بلا موافقة
  - gsm_termux_plan/README.md   : طريقة الاستعمال والشروط

لا adb، لا APK، لا تثبيت، لا(root)، لا SMS/call، لا شبكة. أي تنفيذ كيحتاج
ملف موافقة موقعّن بـ approved_once لكل serial، وSIM READY إلزامي.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_STATE = Path(__file__).resolve().parents[1] / "state"
_PLAN = _STATE / "gsm_termux_plan"
_FORBIDDEN = ("touping.exe",)
_ALLOWED_TASKS = ("status", "battery", "props")

WORKER = '''#!/usr/bin/env python3
"""عامل GSM داخل Termux — قراءة فقط، loopback، بلا root/SMS/call/أوامر عشوائية."""
from __future__ import annotations

import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ALLOWED = ("status", "battery", "props")
TOKEN = os.environ.get("ESPRIE_WORKER_TOKEN", "")
HOST = os.environ.get("ESPRIE_WORKER_HOST", "127.0.0.1")
PORT = int(os.environ.get("ESPRIE_WORKER_PORT", "8765"))


def _read(command):
    try:
        out = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
        return (out.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def task(name):
    if name == "battery":
        return {"level": _read(["dumpsys", "battery"])[:2000]}
    if name == "props":
        keys = ("ro.product.model", "ro.build.version.release", "ro.product.cpu.abi")
        return {key: _read(["getprop", key]) for key in keys}
    if name == "status":
        return {
            "airplane": _read(["settings", "get", "global", "airplane_mode_on"]),
            "sim": _read(["getprop", "gsm.sim.state"]),
        }
    return None


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"ok": True, "allowed": list(ALLOWED), "readOnly": True})
        else:
            self._send(404, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/v1/task":
            self._send(404, {"error": "not_found"})
            return
        if not TOKEN or self.headers.get("X-Worker-Token") != TOKEN:
            self._send(401, {"error": "token_required"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(min(length, 4096)) or b"{}")
        except (ValueError, TypeError):
            self._send(400, {"error": "bad_json"})
            return
        name = body.get("task") if isinstance(body, dict) else None
        if name not in ALLOWED:
            self._send(400, {"error": "task_not_allowed", "allowed": list(ALLOWED)})
            return
        self._send(200, {"task": name, "result": task(name)})

    def log_message(self, *_args):
        return


if __name__ == "__main__":
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
'''

BOOTSTRAP = '''#!/bin/sh
# educativo: أوامر تحضير داخل Termux — كيتقرا غير، ما كيتنفّذش من هاد السكريبت.
set -eu
pkg update -y
pkg install -y python
python -m pip install --no-cache-dir --disable-pip-version-check huggingface_hub || true
echo "ضع worker.py فـ ~/ && TEKRAB: ESPRIE_WORKER_TOKEN=<token> python ~/worker.py"
echo "التحقق: curl -s http://127.0.0.1:8765/health"
'''

README = '''# خطة Termux/GSM — محضّرة بلا تنفيذ

> هادشي **تحضير فقط**. ما تثبّتش APK، ما تدخلش Termux، ما فتحتش ADB TCP، وما لمستش `touping.exe`.

## الملفات
- `worker.py`: عامل قراءة فقط (`status|battery|props`)، اسمعه على `127.0.0.1:8765`، كيطلب `X-Worker-Token`.
- `bootstrap.sh`: أوامر Termux نصّية للمراجعة.
- `plan.json`: كل جهاز `pending`، `approved=false`.

## شرط التنفيذ (لكل جهاز، فكل مرة)
1. serial واضح من `gsm_status.json`.
2. `sim_state=READY` إلزامي.
3. ملف موافقة فيه `approved_once` و`actor` و`action` و`recipient` و`content`، محفوظ فـ`action_requests.json`.
4. تنفيذ عبر `adb -s <serial> shell ...` أو `adb -s <serial> install ...` فقط — بلا `touping.exe`، بلا root، بلا SMS/call.

## الحدود
- التلفون ما كيزيدش RAM الحاسوب. هاد العامل كيوفر تفويض مهام خفيفة غير.
- الذاكرة الحرة المقيسة على الأجهزة الحالية: 111–305 MB → ما تكفيش لاستدلال ثقيل.
- أي ادّعاء `live_verified` كيحتاج benchmark حديث ≤7 أيام.
'''


def _devices(state_dir: Path) -> list[dict[str, Any]]:
    try:
        raw = json.loads((state_dir / "gsm_status.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return []
    devices = raw.get("devices")
    return [d for d in devices if isinstance(d, dict)] if isinstance(devices, list) else []


def build_plan(state_dir: Path = _STATE, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    devices = _devices(state_dir)
    rows = []
    for device in devices:
        serial = str(device.get("serial") or "").strip()
        if not serial:
            continue
        rows.append({
            "serial": serial,
            "model": str(device.get("model") or ""),
            "simState": str(device.get("sim_state") or ""),
            "simReady": str(device.get("sim_state") or "").upper() == "READY",
            "root": bool(device.get("root")),
            "termux": bool(device.get("termux")),
            "freeMb": device.get("free_mb"),
            "state": "pending",
            "approved": False,
            "executed": False,
            "command": None,
        })
    return {
        "generatedAt": now.isoformat().replace("+00:00", "Z"),
        "executor": "adb.exe only",
        "forbiddenBinaries": list(_FORBIDDEN),
        "allowedTasks": list(_ALLOWED_TASKS),
        "targetDevices": 20,
        "deviceCount": len(rows),
        "devices": rows,
        "note": "Preparation only. No installation, no device action, no network.",
    }


def render_command(serial: str, approval: dict[str, Any] | None, state_dir: Path = _STATE) -> str | None:
    """يرجّع نصّ أمر للمراجعة فقط، وإلا None. ما كينفّذو حتى واحد."""
    if not isinstance(approval, dict):
        return None
    if approval.get("state") != "approved_once" or not approval.get("actor"):
        return None
    if str(approval.get("serial") or "") != serial:
        return None
    if not str(approval.get("action") or "").startswith("gsm_termux_"):
        return None
    if not str(approval.get("recipient") or "").strip() or not str(approval.get("content") or "").strip():
        return None
    device = next((d for d in _devices(state_dir) if str(d.get("serial")) == serial), None)
    if not device or str(device.get("sim_state") or "").upper() != "READY":
        return None
    kind = str(approval.get("action"))
    suffix = "shell sh /sdcard/termux-bootstrap.sh" if kind == "gsm_termux_bootstrap" else "install worker.apk"
    return f'adb -s {serial} {suffix}'


def prepare(state_dir: Path = _STATE, target: Path | None = None) -> Path:
    state_dir = Path(state_dir)
    plan_dir = Path(target) if target else state_dir / "gsm_termux_plan"
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / "worker.py").write_text(WORKER, encoding="utf-8")
    (plan_dir / "bootstrap.sh").write_text(BOOTSTRAP, encoding="utf-8")
    (plan_dir / "README.md").write_text(README, encoding="utf-8")
    plan = build_plan(state_dir)
    fd, tmp = tempfile.mkstemp(prefix="gsm_termux_plan.", suffix=".tmp", dir=str(plan_dir))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(plan, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp, plan_dir / "plan.json")
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return plan_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare GSM Termux payload without executing it")
    parser.add_argument("--state-dir", default=str(_STATE))
    parser.add_argument("--target", default="")
    args = parser.parse_args()
    target = Path(args.target) if args.target else None
    path = prepare(Path(args.state_dir), target)
    plan = json.loads((path / "plan.json").read_text(encoding="utf-8"))
    print(f"prepared {path} devices={plan['deviceCount']} approved=0 executed=0 touping=never")


if __name__ == "__main__":
    main()
