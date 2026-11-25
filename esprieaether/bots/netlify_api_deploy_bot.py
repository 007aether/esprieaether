#!/usr/bin/env python3
"""
netlify_api_deploy_bot.py — deploy Sunna site to Netlify via direct API

WHAT: Creates (or reuses) a Netlify site and deploys
../Sunna-Equipe-Industrial/Site_Public/ as a direct file upload
(NO git push, NO build step — the site is static HTML/CSS/JS).

WHY API instead of CLI:
  - CLI needs interactive `netlify login` (browser auth).
  - API with a Personal Access Token is fully non-interactive —
    the autonomous loop can deploy automatically.
  - Token comes from NETLIFY_AUTH_TOKEN in .env (never printed).

FLOW (Netlify direct deploy):
  1. Find or create the site (POST /api/v1/{account}/sites).
  2. Deploy files: create deploy with required files → upload each
     file hash → POST /api/v1/deploys with the file digest.
  3. Poll until deploy is ready → return live URL.

Usage:
  python netlify_api_deploy_bot.py              # deploy (auto-create site)
  python netlify_api_deploy_bot.py --check      # verify token + list sites
  python netlify_api_deploy_bot.py --url        # print live URL
"""

import base64
import hashlib
import json
import logging
import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SUNNA_DIR = BASE_DIR.parent / "Sunna-Equipe-Industrial" / "Site_Public"
STATE_FILE = BASE_DIR / "data" / "netlify_state.json"
LOG_FILE = BASE_DIR / "data" / "logs" / "netlify_deploy.log"

logger = logging.getLogger("netlify_api_deploy_bot")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

API = "https://api.netlify.com/api/v1"
DEFAULT_SITE_NAME = "sunna-metal"
# files to skip
SKIP_EXT = {".part", ".tmp", ".log", ".pyc"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB per file (Netlify limit-ish)


def get_token():
    """Read NETLIFY_AUTH_TOKEN from .env (never logged)."""
    env = BASE_DIR / ".env"
    if not env.exists():
        return None
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("NETLIFY_AUTH_TOKEN="):
            return line.split("=", 1)[1].strip()
    return None


def api(method, path, token, body=None, raw=False):
    """Call the Netlify API. Returns (status, json_or_text)."""
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            text = r.read().decode("utf-8", "replace")
            if raw:
                return r.status, text
            try:
                return r.status, json.loads(text)
            except json.JSONDecodeError:
                return r.status, text
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(text)
        except json.JSONDecodeError:
            return e.code, text
    except Exception as e:
        return 0, str(e)


def account_slug(token):
    """Get the account slug (for site creation path /{account_slug}/sites)."""
    st, data = api("GET", "/user", token)
    if st == 200 and isinstance(data, dict):
        return data.get("slug") or data.get("id")
    return None


def find_or_create_site(token, name):
    """Return (site_id, site_url, ssl_url, created_bool)."""
    # list sites
    st, sites = api("GET", "/sites", token)
    if st == 200 and isinstance(sites, list):
        for s in sites:
            if s.get("name") == name:
                logger.info(f"site exists: {s.get('ssl_url') or s.get('url')}")
                return s["id"], s.get("url"), s.get("ssl_url"), False

    # create
    acct = account_slug(token)
    if not acct:
        raise RuntimeError("could not resolve account slug")
    logger.info(f"creating site '{name}' ...")
    st, site = api("POST", f"/{acct}/sites", token, body={"name": name})
    if not (st in (200, 201) and isinstance(site, dict)):
        # retry: some accounts need the site created via /sites with subdomain
        logger.warning(f"create via /{acct}/sites failed ({st}), trying /sites ...")
        st, site = api("POST", "/sites", token, body={"name": name})
    if st in (200, 201) and isinstance(site, dict):
        logger.info(f"created: {site.get('ssl_url') or site.get('url')}")
        return site["id"], site.get("url"), site.get("ssl_url"), True
    raise RuntimeError(f"site create failed ({st}): {str(site)[:200]}")


def sha1_file(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def deploy(token, site_id, publish_dir):
    """Deploy files via the Netlify file-digest API."""
    # 1. collect files (relative paths)
    files = {}
    for root, dirs, names in os.walk(publish_dir):
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".git")]
        for n in names:
            p = Path(root) / n
            if p.suffix.lower() in SKIP_EXT:
                continue
            if p.stat().st_size > MAX_FILE_SIZE:
                logger.warning(f"skip (too big): {p}")
                continue
            rel = p.relative_to(publish_dir).as_posix()
            files[rel] = p

    if not files:
        raise RuntimeError(f"no files to deploy in {publish_dir}")
    logger.info(f"deploying {len(files)} files ...")

    # 2. create deploy with file hashes (sha1 = required, sha256 optional)
    file_hashes = {rel: sha1_file(p) for rel, p in files.items()}
    st, deploy = api("POST", f"/sites/{site_id}/deploys", token,
                     body={"files": file_hashes})
    if not (st in (200, 201) and isinstance(deploy, dict)):
        raise RuntimeError(f"deploy create failed ({st}): {str(deploy)[:200]}")

    deploy_id = deploy["id"]
    required = deploy.get("required", [])
    logger.info(f"deploy {deploy_id}: {len(required)} files to upload")

    # 3. upload each required file
    for rel_hash in required:
        rel = None
        for r, h in file_hashes.items():
            if h == rel_hash:
                rel = r
                break
        if rel is None:
            logger.warning(f"unknown hash {rel_hash[:12]}, skipping")
            continue
        p = files[rel]
        with open(p, "rb") as f:
            content = f.read()
        # PUT raw bytes
        req = urllib.request.Request(
            f"{API}/deploys/{deploy_id}/files/{rel}",
            data=content, method="PUT")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/octet-stream")
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                r.read()
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"upload failed for {rel} ({e.code}): {e.read()[:200]}")

    logger.info("all files uploaded, waiting for deploy to go live ...")

    # 4. poll until ready
    for _ in range(60):
        st, d = api("GET", f"/deploys/{deploy_id}", token)
        state = d.get("state") if isinstance(d, dict) else "?"
        if state == "ready":
            return d
        if state == "error":
            raise RuntimeError(f"deploy errored: {str(d)[:200]}")
        time.sleep(3)

    raise RuntimeError("deploy did not become ready in time")


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


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--url", action="store_true")
    ap.add_argument("--site", default=DEFAULT_SITE_NAME)
    args = ap.parse_args()

    token = get_token()
    if not token:
        print("❌ NETLIFY_AUTH_TOKEN not in .env")
        print("   get one: https://app.netlify.com/user/applications#personal-access-tokens")
        return 1

    # verify token
    st, user = api("GET", "/user", token)
    if st != 200:
        print(f"❌ token invalid ({st}): {str(user)[:150]}")
        return 1
    print(f"✅ token OK — {user.get('email', '?')}")

    if args.check:
        st, sites = api("GET", "/sites", token)
        if st == 200 and isinstance(sites, list):
            print(f"✅ {len(sites)} site(s):")
            for s in sites:
                print(f"   {s.get('name')} → {s.get('ssl_url') or s.get('url')}")
        return 0

    state = load_state()

    if args.url:
        sid = state.get("site_id")
        if not sid:
            print("(no site deployed yet)")
            return 0
        st, site = api("GET", f"/sites/{sid}", token)
        url = site.get("ssl_url") or site.get("url") if isinstance(site, dict) else "?"
        print(url)
        return 0

    # full deploy
    if not SUNNA_DIR.exists():
        print(f"❌ publish dir missing: {SUNNA_DIR}")
        return 1

    try:
        sid, url, ssl, created = find_or_create_site(token, args.site)
        print(f"🌐 site: {ssl or url} ({'created' if created else 'existing'})")
        result = deploy(token, sid, str(SUNNA_DIR))
        live = result.get("ssl_url") or result.get("url") or ssl or url
        save_state(site_id=sid, url=live,
                   last_deploy=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                   deploy_id=result.get("id"))
        print(f"✅ LIVE → {live}")
        return 0
    except Exception as e:
        logger.error(f"❌ deploy failed: {e}")
        print(f"❌ {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
