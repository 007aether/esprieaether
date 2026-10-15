#!/usr/bin/env python3
"""
netlify_deploy_bot.py — deploy Sunna site to Netlify via CLI (no manual token)

WHAT: Wraps the Netlify CLI (npx netlify-cli) to deploy
../Sunna-Equipe-Industrial/Site_Public/ to a Netlify site.

WHY CLI instead of API token:
  - The API token (NETLIFY_AUTH_TOKEN in .env) expired (401).
  - Netlify CLI uses browser-based OAuth: run `netlify login` once
    (opens browser, saves creds locally), then all deploys are automatic.
  - No tokens in .env, no 401s, no manual token regeneration.

FLOW:
  1. Check if netlify-cli is installed (npx netlify-cli --version).
  2. Check if authenticated (netlify status) — if not, prompt user once.
  3. Link/create site (netlify link or netlify init).
  4. Deploy: netlify deploy --prod --dir Site_Public --site <name>.

Usage:
  python netlify_deploy_bot.py              # deploy if authenticated
  python netlify_deploy_bot.py --check      # check auth + CLI only
  python netlify_deploy_bot.py --url        # print current site URL
"""

import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SUNNA_DIR = BASE_DIR.parent / "Sunna-Equipe-Industrial" / "Site_Public"
STATUS_FILE = BASE_DIR / "data" / "netlify_status.json"
LOG_FILE = BASE_DIR / "data" / "logs" / "netlify_deploy.log"

logger = logging.getLogger("netlify_deploy_bot")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

CLI_TIMEOUT = 120  # seconds per netlify command


def run_netlify(args, timeout=CLI_TIMEOUT, capture=True):
    """Run a netlify CLI command, return (returncode, stdout, stderr)."""
    cmd = ["npx", "--yes", "netlify-cli"] + args
    logger.info(f"$ {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, capture_output=capture, text=True, timeout=timeout,
                           cwd=str(SUNNA_DIR), shell=True)
        return r.returncode, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", f"TIMEOUT after {timeout}s"
    except Exception as e:
        return -1, "", str(e)


def check_cli():
    """Is netlify-cli available?"""
    rc, out, err = run_netlify(["--version"], timeout=60)
    return rc == 0, out.strip()


def check_auth():
    """Are we authenticated? netlify status returns 0 + JSON if yes."""
    rc, out, err = run_netlify(["status", "--json"], timeout=30)
    if rc == 0 and out.strip().startswith("{"):
        try:
            data = json.loads(out)
            return True, data
        except json.JSONDecodeError:
            return False, {}
    return False, {}


def get_site_url(status_data):
    """Extract site URL from netlify status JSON."""
    # netlify status --json returns {"account": {...}, "siteData": {...}}
    site = status_data.get("siteData", {})
    return site.get("ssl_url") or site.get("url") or site.get("admin_url", "")


def deploy():
    """Deploy Site_Public to Netlify (production)."""
    if not SUNNA_DIR.exists():
        logger.error(f"Sunna site dir not found: {SUNNA_DIR}")
        return {"status": "error", "error": "Site_Public missing"}

    # deploy (prod)
    rc, out, err = run_netlify(["deploy", "--prod", "--dir", "."], timeout=600)
    if rc == 0:
        # extract URL from output
        url = ""
        for line in out.splitlines():
            if "Website URL" in line or "netlify.app" in line:
                url = line.strip()
                break
        # save status
        STATUS_FILE.parent.mkdir(exist_ok=True)
        STATUS_FILE.write_text(json.dumps({
            "last_deploy": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "status": "ok",
            "url": url,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"✅ deployed → {url or 'see output'}")
        return {"status": "ok", "url": url, "output": out[-500:]}
    else:
        logger.error(f"❌ deploy failed: {err[:200]}")
        return {"status": "error", "error": err[:200]}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="check CLI + auth only")
    ap.add_argument("--url", action="store_true", help="print current site URL")
    ap.add_argument("--deploy", action="store_true", help="force deploy now")
    args = ap.parse_args()

    # 1. CLI check
    cli_ok, cli_ver = check_cli()
    if not cli_ok:
        print(f"❌ netlify-cli not available: {cli_ver}")
        print("   install: npm i -g netlify-cli")
        return 1
    print(f"✅ netlify-cli {cli_ver}")

    # 2. auth check
    auth_ok, status = check_auth()
    if not auth_ok:
        print("❌ not authenticated with Netlify")
        print("   run: netlify login   (opens browser, one-time)")
        print("   or:  npx netlify-cli login")
        return 1
    print("✅ authenticated")

    if args.check:
        url = get_site_url(status)
        print(f"✅ site: {url or '(not linked)'}")
        return 0

    if args.url:
        url = get_site_url(status)
        print(url or "(no site linked)")
        return 0

    # 3. deploy
    if args.deploy or True:  # default = deploy
        result = deploy()
        if result["status"] == "ok":
            print(f"✅ deployed → {result.get('url', '?')}")
            return 0
        else:
            print(f"❌ deploy failed: {result.get('error', '?')}")
            return 1


if __name__ == "__main__":
    sys.exit(main())
