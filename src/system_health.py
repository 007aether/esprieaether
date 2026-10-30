"""EsprieAether — Unified System Health

Single place to check whether core services are alive.
Used by: dashboard, Telegram /status, watchdog, start_all, autonome_evolve.

Usage:
    python -m src.system_health
    from src.system_health import get_full_report, is_healthy
"""

from __future__ import annotations

import json
import os
import socket
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    requests = None  # type: ignore

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""
    latency_ms: float | None = None


@dataclass
class HealthReport:
    timestamp: str
    overall_ok: bool
    checks: list[CheckResult] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "overall_ok": self.overall_ok,
            "summary": self.summary,
            "checks": [asdict(c) for c in self.checks],
        }


def _port_open(host: str, port: int, timeout: float = 1.5) -> tuple[bool, float]:
    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            latency = (time.perf_counter() - start) * 1000
            return True, latency
    except OSError:
        return False, (time.perf_counter() - start) * 1000


def _http_ok(url: str, timeout: float = 2.0) -> tuple[bool, float, str]:
    if requests is None:
        return False, 0.0, "requests not installed"
    start = time.perf_counter()
    try:
        r = requests.get(url, timeout=timeout)
        latency = (time.perf_counter() - start) * 1000
        ok = 200 <= r.status_code < 500
        return ok, latency, f"HTTP {r.status_code}"
    except Exception as e:
        return False, (time.perf_counter() - start) * 1000, str(e)[:80]


def check_ollama() -> CheckResult:
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").replace("http://", "").split("/")[0]
    if ":" in host:
        h, p = host.split(":", 1)
        port = int(p)
    else:
        h, port = host or "localhost", 11434
    ok, latency = _port_open(h, port)
    return CheckResult("ollama", ok, "port open" if ok else "unreachable", latency)


def check_router() -> CheckResult:
    port = int(os.environ.get("ROUTER_PORT", "11435"))
    ok, latency = _port_open("127.0.0.1", port)
    return CheckResult("ai_router", ok, f":{port}", latency)


def check_web() -> CheckResult:
    port = int(os.environ.get("WEB_PORT", "5000"))
    ok, latency = _port_open("127.0.0.1", port)
    if ok and requests:
        http_ok, lat2, detail = _http_ok(f"http://127.0.0.1:{port}/")
        return CheckResult("web_dashboard", http_ok or ok, detail or f":{port}", lat2 or latency)
    return CheckResult("web_dashboard", ok, f":{port}", latency)


def check_cloud_desktop() -> CheckResult:
    port = int(os.environ.get("CLOUD_DESKTOP_PORT", "5001"))
    ok, latency = _port_open("127.0.0.1", port)
    return CheckResult("cloud_desktop", ok, f":{port}", latency)


def check_trade_cycle_db() -> CheckResult:
    candidates = [
        ROOT / "work" / "data" / "trade_cycle.db",
        ROOT / "work" / "agents" / "trade_cycle" / "trade_cycle.db",
        ROOT / "data" / "trade_cycle.db",
    ]
    for path in candidates:
        if path.exists():
            size = path.stat().st_size
            return CheckResult("trade_cycle_db", True, f"{path.name} ({size} bytes)")
    return CheckResult("trade_cycle_db", False, "database not found (run loop once to create)")


def check_env() -> CheckResult:
    missing = []
    # Soft checks — only warn
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        missing.append("TELEGRAM_BOT_TOKEN")
    if not os.environ.get("TELEGRAM_CHAT_ID"):
        missing.append("TELEGRAM_CHAT_ID")
    if missing:
        return CheckResult("env_telegram", False, f"missing: {', '.join(missing)}")
    return CheckResult("env_telegram", True, "token + chat_id set")


def get_full_report() -> HealthReport:
    checks = [
        check_ollama(),
        check_router(),
        check_web(),
        check_cloud_desktop(),
        check_trade_cycle_db(),
        check_env(),
    ]
    # Core services that must be up for "healthy"
    core = {"ollama", "web_dashboard"}
    core_ok = all(c.ok for c in checks if c.name in core)
    overall = core_ok  # soft overall: core must pass

    failed = [c.name for c in checks if not c.ok]
    if overall and not failed:
        summary = "All systems nominal"
    elif overall:
        summary = f"Core OK · warnings: {', '.join(failed)}"
    else:
        summary = f"Degraded · failed: {', '.join(failed)}"

    return HealthReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
        overall_ok=overall,
        checks=checks,
        summary=summary,
    )


def is_healthy() -> bool:
    return get_full_report().overall_ok


def format_report_text(report: HealthReport | None = None) -> str:
    report = report or get_full_report()
    lines = [
        f"⚡ EsprieAether Health — {report.timestamp[:19]}Z",
        f"Overall: {'✅ OK' if report.overall_ok else '⚠️ DEGRADED'}",
        f"{report.summary}",
        "",
    ]
    for c in report.checks:
        icon = "✅" if c.ok else "❌"
        lat = f" ({c.latency_ms:.0f}ms)" if c.latency_ms is not None else ""
        lines.append(f"{icon} {c.name}: {c.detail}{lat}")
    return "\n".join(lines)


if __name__ == "__main__":
    report = get_full_report()
    print(format_report_text(report))
    print()
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
