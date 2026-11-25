"""Preuve locale, sans réseau, que la garde de sortie est bien active."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

SRC = Path(__file__).resolve().parent
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from egress_guard import is_loopback_url, is_public_https_url, assert_loopback_url  # noqa: E402
import jarvis_bridge  # noqa: E402

BLOCKED_MODELS = (
    "http://api.example.com/v1",
    "http://192.168.1.10:11434",
    "http://user:pw@127.0.0.1:31416",
)
BLOCKED_WEB = (
    "https://127.0.0.1/",
    "https://192.168.1.10/",
    "https://intranet.local/",
)
ALLOWED_WEB = ("https://news.ycombinator.com/",)


def run_checks() -> dict:
    model_hosts = [jarvis_bridge.DEFAULT_HOST]
    atulya_base = os.getenv("ATULYA_MODEL_BASE_URL", "").strip()
    if atulya_base:
        model_hosts.append(atulya_base)
    for url in model_hosts:
        assert_loopback_url(url)
    for url in BLOCKED_MODELS:
        assert not is_loopback_url(url), url
    for url in BLOCKED_WEB:
        assert not is_public_https_url(url), url
    for url in ALLOWED_WEB:
        assert is_public_https_url(url), url
    return {
        "ok": True,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "engine": "egress_guard",
        "loopbackOnly": True,
        "webLinksPublicHttpsOnly": True,
        "modelHost": jarvis_bridge.DEFAULT_HOST,
        "testedModelHosts": model_hosts,
        "blocked": list(BLOCKED_MODELS + BLOCKED_WEB),
        "allowedPublicLinks": list(ALLOWED_WEB),
    }


def main() -> None:
    state_path = Path(__file__).resolve().parents[1] / "state" / "egress_selfcheck.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(run_checks(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(state_path), "ok": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
