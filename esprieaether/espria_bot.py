"""Générateur de rapport EspriaAether — mode dry-run par défaut, jamais de réseau Telegram implicite.

Usage:
    .venv\\Scripts\\python.exe espria_bot.py            # rapport local, aucun envoi
    .venv\\Scripts\\python.exe espria_bot.py --live      # nécessite TELEGRAM_LIVE=1 et une cible explicite
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / os.getenv("BOT_ENV_FILE", ".env.bot1"))

GATEWAY = os.getenv("ESPRIA_GATEWAY_URL", "http://127.0.0.1:5001").rstrip("/")
LOG_DIR = BASE_DIR / os.getenv("BOT_LOG_DIR", "data/logs")


class BotRunner:
    def __init__(self):
        self.live = os.getenv("TELEGRAM_LIVE", "0") == "1"
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.name = os.getenv("BOT_NAME", "espria-bot")

    def _get_json(self, path: str) -> dict:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(GATEWAY + path)
            response.raise_for_status()
            return response.json()

    def build_report(self) -> str:
        director = self._get_json("/agents/director/run")
        kpis = self._get_json("/kpi/all")
        summary = director.get("summary", {})
        lines = [
            f"تقرير {self.name} — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"الوكلاء: {summary.get('agents_total', 0)}",
            f"المنتجات: {summary.get('products_count', 0)}",
            f"المهام: {summary.get('todo_count', 0)}",
            f"المؤشرات المسجلة: {len(kpis) if isinstance(kpis, list) else 0}",
        ]
        if isinstance(kpis, list):
            for row in kpis[:5]:
                lines.append(f"- {row.get('metric')}: {row.get('count')}")
        return "\n".join(lines)

    def send(self, text: str) -> dict:
        if not self.live:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            log_path = LOG_DIR / "bot_test.log"
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(f"--- {datetime.now().isoformat()} [{self.name}] ---\n{text}\n")
            return {"mode": "dry_run", "delivered": False, "log": str(log_path)}

        if not self.token or not self.chat_id:
            return {"mode": "live", "delivered": False, "error": "Clé ou chat cible absent"}
        try:
            response = httpx.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={"chat_id": self.chat_id, "text": text},
                timeout=15.0,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            return {
                "mode": "live",
                "delivered": False,
                "error": f"Telegram HTTP {exc.response.status_code} — identifiants refusés",
            }
        except httpx.HTTPError as exc:
            return {"mode": "live", "delivered": False, "error": f"Erreur réseau Telegram ({type(exc).__name__})"}
        return {"mode": "live", "delivered": True, "status_code": response.status_code}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    bot = BotRunner()
    if "--live" in sys.argv and not bot.live:
        print("TELEGRAM_LIVE doit être positionné à 1 explicitement.", file=sys.stderr)
        return 2
    report = bot.build_report()
    result = bot.send(report)
    print(json.dumps({"report": report, "send": result}, ensure_ascii=False, indent=2))
    if result.get("mode") == "live" and not result.get("delivered"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
