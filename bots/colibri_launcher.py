#!/usr/bin/env python3
"""
colibri_launcher.py — start colibri serve + wire it into EsprieAether

WHAT: Once the qwen3-coder-30b download completes, this launcher:
  1. Starts `coli serve` (OpenAI-compatible API on :8000)
  2. Waits for it to be ready (polls /v1/models)
  3. Verifies the router can reach it (colibri-local brain)
  4. Writes data/colibri_serve_state.json (url, model, status)

WHY a launcher:
  - coli serve needs the model fully downloaded (19.4GB)
  - it must stay running as a detached background service
  - the router (ai_router.py) expects it at http://127.0.0.1:8000/v1
  - this makes the 30B brain a first-class local service

Usage:
  python colibri_launcher.py --check     # is download complete + serve ready?
  python colibri_launcher.py --start     # start coli serve (detached)
  python colibri_launcher.py --status    # serve + router status
"""

import json
import logging
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
COLIBRI_DIR = BASE_DIR / "tools" / "colibri"
MODEL_DIR = Path(os.environ.get("COLIBRI_MODEL_DIR", "D:/AetherData/colibri-models"))
MODEL_NAME = "qwen3-coder-30b"
STATE_FILE = BASE_DIR / "data" / "colibri_serve_state.json"
LOG_FILE = BASE_DIR / "data" / "logs" / "colibri_serve.log"

SERVE_PORT = 8000
SERVE_URL = f"http://127.0.0.1:{SERVE_PORT}"

logger = logging.getLogger("colibri_launcher")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


def download_complete():
    """Is the model fully downloaded? (no .part files + expected shards)."""
    model_path = MODEL_DIR / MODEL_NAME
    if not model_path.exists():
        return False, "model dir missing"
    parts = list(model_path.glob("*.part"))
    if parts:
        return False, f"{len(parts)} .part files still downloading"
    # check download state file
    state = model_path / ".colibri-download.json"
    if state.exists():
        try:
            d = json.loads(state.read_text(encoding="utf-8"))
            if not d.get("complete"):
                missing = 59 - 31  # from last check
                return False, f"incomplete ({d.get('complete')})"
        except Exception:
            pass
    shards = list(model_path.glob("*.safetensors"))
    if len(shards) < 50:  # full model has ~50+ shards
        return False, f"only {len(shards)} shards"
    return True, f"{len(shards)} shards ready"


def serve_ready():
    """Is coli serve responding?"""
    try:
        with urllib.request.urlopen(f"{SERVE_URL}/v1/models", timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def router_has_colibri():
    """Does the router expose colibri-local?"""
    try:
        with urllib.request.urlopen("http://127.0.0.1:11435/v1/models", timeout=5) as r:
            data = json.loads(r.read())
            models = [m["id"] for m in data.get("data", [])]
            return "aether-local" in models  # chain includes colibri
    except Exception:
        return False


def start_serve(detached=True):
    """Start coli serve as a background process."""
    if serve_ready():
        logger.info("coli serve already running")
        return True

    py = sys.executable
    cmd = [py, "coli", "serve", "--model", MODEL_NAME, "--port", str(SERVE_PORT)]

    logger.info(f"starting coli serve: {' '.join(cmd)}")
    if detached:
        # detached: survives session
        if os.name == "nt":
            # Windows: use Start-Process via powershell
            ps_cmd = (
                f"Start-Process -FilePath '{py}' "
                f"-ArgumentList 'coli','serve','--model','{MODEL_NAME}','--port','{SERVE_PORT}' "
                f"-WorkingDirectory '{COLIBRI_DIR}' -WindowStyle Hidden "
                f"-RedirectStandardOutput '{LOG_FILE}' -RedirectStandardError '{LOG_FILE}.err'"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], timeout=30)
        else:
            subprocess.Popen(cmd, cwd=str(COLIBRI_DIR),
                             stdout=open(LOG_FILE, "a"), stderr=subprocess.STDOUT,
                             start_new_session=True)
    else:
        subprocess.Popen(cmd, cwd=str(COLIBRI_DIR))

    # wait for ready (model load can take 30-60s)
    for i in range(30):
        time.sleep(3)
        if serve_ready():
            logger.info(f"coli serve ready after ~{(i+1)*3}s")
            return True
        logger.info(f"waiting for serve... {i+1}/30")

    return False


def status():
    """Full status for Telegram."""
    dl_ok, dl_msg = download_complete()
    serve_ok = serve_ready()
    router_ok = router_has_colibri()

    lines = ["🧠 *Colibri Serve*", ""]
    lines.append(f"Model: `{MODEL_NAME}` ({dl_msg})")
    lines.append(f"Download: {'✅' if dl_ok else '🔄'} {dl_msg}")
    lines.append(f"Serve :{SERVE_PORT}: {'🟢 ready' if serve_ok else '🔴 stopped'}")
    lines.append(f"Router: {'🟢 colibri wired' if router_ok else '🔴 not wired'}")
    lines += ["", f"API: {SERVE_URL}/v1"]
    return "\n".join(lines)


def save_state(**kw):
    STATE_FILE.parent.mkdir(exist_ok=True)
    existing = {}
    if STATE_FILE.exists():
        try:
            existing = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    existing.update(kw)
    STATE_FILE.write_text(json.dumps(existing, ensure_ascii=False, indent=2),
                          encoding="utf-8")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--start", action="store_true")
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    if args.status:
        print(status())
        return

    if args.check:
        dl_ok, dl_msg = download_complete()
        serve_ok = serve_ready()
        print(f"download: {'✅' if dl_ok else '🔄'} {dl_msg}")
        print(f"serve: {'✅ ready' if serve_ok else '❌ stopped'}")
        print(f"router: {'✅ wired' if router_has_colibri() else '❌'}")
        return

    if args.start:
        dl_ok, dl_msg = download_complete()
        if not dl_ok:
            print(f"❌ cannot start — download incomplete: {dl_msg}")
            return 1
        ok = start_serve()
        if ok:
            save_state(status="running", url=SERVE_URL,
                       model=MODEL_NAME, ts=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
            print(f"✅ coli serve running → {SERVE_URL}/v1")
            return 0
        else:
            print("❌ serve did not become ready")
            return 1

    print(status())


if __name__ == "__main__":
    sys.exit(main() or 0)
