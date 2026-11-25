#!/usr/bin/env python3
"""
backup_agent.py — encrypted backup of the EsprieAether + Sunna data

WHAT: Tars the essential data of both repos (catalogue, devis, factures,
veille index, vector memory, board, config) into one archive, encrypts it
with a passphrase (AES via stdlib only — Fernet from cryptography if
available, else a simple XOR+HMAC fallback), and uploads it to a private
GitHub repo (the free cloud) as a release-style artifact.

WHY: a full disk failure or a bad auto_apply run destroys months of work.
Git covers the code; this covers the DATA (json databases, logs, catalogues)
that git deliberately ignores or that live in a second non-git workspace.

Usage:
  python backup_agent.py --apply            # create + encrypt + upload
  python backup_agent.py --dry-run          # show what would be backed up
  python backup_agent.py --list             # list remote backups
  python backup_agent.py --restore <file>   # decrypt + extract a backup
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
except ImportError:
    pass

HOME = Path.home()
ESPIRE = HOME / "Desktop" / "esprieaether"
SUNNA = HOME / "Desktop" / "Sunna-Equipe-Industrial"
BACKUP_DIR = HOME / "ESPRIEAETHER" / "backups"

# what gets backed up (relative to each workspace root)
ESPIRE_DATA = [
    "data/agent_board.json",
    "data/agent_proposed_tasks.json",
    "data/airdrop_scored.json",
    "data/veille_index.json",
    "data/vector_memory.db",
    "data/cloud_status.json",
    "data/cloud_commands.json",
    "data/group.json",
    ".env",
]
SUNNA_DATA = [
    "Catalogue/catalogue.json",
    "Catalogue/images_concurrents",
    "Devis",
    "Factures",
    "Recherche/live_prices.json",
    "Recherche/cost_estimates.json",
    "Bilans",
    "Veille/base_veille.json",
]

# max total archive size before warning (100 MB)
MAX_SIZE_MB = 100


def collect_files():
    """All files to back up: (abs_path, archive_name)."""
    files = []
    for rel in ESPIRE_DATA:
        p = ESPIRE / rel
        if p.exists():
            files.append((p, f"esprieaether/{rel}"))
    for rel in SUNNA_DATA:
        p = SUNNA / rel
        if p.exists():
            files.append((p, f"sunna/{rel}"))
    return files


def create_archive(out_path, files):
    """Tar.gz the collected files (dirs recursed)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with tarfile.open(out_path, "w:gz") as tar:
        for src, arcname in files:
            if src.is_dir():
                for f in sorted(src.rglob("*")):
                    if f.is_file():
                        tar.add(f, arcname=f"{arcname}/{f.relative_to(src)}")
                        count += 1
            else:
                tar.add(src, arcname=arcname)
                count += 1
    return count


# ── Encryption ──

def _derive_key(passphrase, salt):
    return hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, 200_000, dklen=32)


def encrypt_file(src, dst, passphrase):
    """Encrypt with Fernet if available, else AES-CBC-free XOR+HMAC stream."""
    try:
        from cryptography.fernet import Fernet
        key = base64.urlsafe_b64encode(hashlib.sha256(passphrase.encode()).digest())
        f = Fernet(key)
        data = src.read_bytes()
        dst.write_bytes(f.encrypt(data))
        return "fernet"
    except ImportError:
        pass

    # stdlib fallback: PBKDF2 key stream + HMAC integrity
    salt = os.urandom(16)
    key = _derive_key(passphrase, salt)
    data = src.read_bytes()
    stream = hashlib.sha256(key + b"\x00").digest()
    out = bytearray()
    idx = 0
    while len(out) < len(data):
        for b in stream:
            out.append(b)
            if len(out) >= len(data):
                break
        idx += 1
        stream = hashlib.sha256(key + idx.to_bytes(4, "big")).digest()
    cipher = bytes(a ^ b for a, b in zip(data, out))
    mac = hmac.new(key, cipher, hashlib.sha256).digest()
    dst.write_bytes(salt + mac + cipher)
    return "stdlib-hmac"


def decrypt_file(src, dst, passphrase):
    """Reverse of encrypt_file."""
    try:
        from cryptography.fernet import Fernet
        key = base64.urlsafe_b64encode(hashlib.sha256(passphrase.encode()).digest())
        f = Fernet(key)
        dst.write_bytes(f.decrypt(src.read_bytes()))
        return "fernet"
    except ImportError:
        pass

    blob = src.read_bytes()
    salt, mac, cipher = blob[:16], blob[16:48], blob[48:]
    key = _derive_key(passphrase, salt)
    expected = hmac.new(key, cipher, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected):
        raise ValueError("HMAC mismatch — wrong passphrase or corrupted file")
    stream = hashlib.sha256(key + b"\x00").digest()
    out_len = len(cipher)
    full = bytearray()
    idx = 0
    while len(full) < out_len:
        for b in stream:
            full.append(b)
            if len(full) >= out_len:
                break
        idx += 1
        stream = hashlib.sha256(key + idx.to_bytes(4, "big")).digest()
    plain = bytes(a ^ b for a, b in zip(cipher, full))
    dst.write_bytes(plain)
    return "stdlib-hmac"


def get_passphrase():
    """From env or fail — never hardcode."""
    pp = os.getenv("AETHER_BACKUP_KEY", "")
    if not pp:
        # derive from git remote + a known file so it's stable per machine
        seed_file = ESPIRE / "data" / ".backup_seed"
        if seed_file.exists():
            pp = seed_file.read_text(encoding="utf-8").strip()
    return pp


def upload_github(enc_path, repo="007aether/esprieaether-backups"):
    """Upload encrypted archive to a private repo via git (or gh if available)."""
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        return {"ok": False, "reason": "no GITHUB_TOKEN in env"}

    # use gh CLI when present
    gh = shutil.which("gh")
    if gh and token:
        try:
            env = dict(os.environ, GH_TOKEN=token)
            r = subprocess.run(
                [gh, "release", "create", f"backup-{datetime.now(timezone.utc):%Y%m%d-%H%M}",
                 str(enc_path), "--repo", repo, "--title", "Encrypted backup"],
                capture_output=True, text=True, timeout=120, env=env,
            )
            if r.returncode == 0:
                return {"ok": True, "where": f"github release {repo}"}
        except Exception:
            pass

    # git push to the backup repo
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=tmp, timeout=30)
            subprocess.run(["git", "checkout", "-q", "-b", "main"], cwd=tmp, timeout=30)
            shutil.copy(enc_path, tmp / enc_path.name)
            subprocess.run(["git", "add", "-A"], cwd=tmp, timeout=30)
            subprocess.run(
                ["git", "-c", "user.name=aether-backup", "-c", "user.email=backup@aether.local",
                 "commit", "-q", "-m", f"backup {datetime.now(timezone.utc):%Y-%m-%d %H:%M}"],
                cwd=tmp, timeout=30,
            )
            url = f"https://x-access-token:{token}@github.com/{repo}.git"
            env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_ASKPASS="echo")
            r = subprocess.run(
                ["git", "push", url, "main", "--force"],
                cwd=tmp, capture_output=True, text=True, timeout=180, env=env,
            )
            if r.returncode == 0:
                return {"ok": True, "where": f"github repo {repo}"}
            return {"ok": False, "reason": (r.stderr or "")[:200]}
    except Exception as e:
        return {"ok": False, "reason": str(e)[:200]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--restore", help="decrypt + extract a backup file")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    files = collect_files()
    total_bytes = sum(f.stat().st_size for f, _ in files if f.is_file())

    if args.dry_run:
        print(f"📦 {len(files)} entries, {total_bytes/1024/1024:.1f} MB")
        for f, arc in files[:20]:
            size = f.stat().st_size if f.is_file() else sum(x.stat().st_size for x in f.rglob('*') if x.is_file())
            print(f"  {size/1024:8.1f} KB  {arc}")
        if len(files) > 20:
            print(f"  ... +{len(files)-20} more")
        return

    if args.restore:
        pp = get_passphrase()
        if not pp:
            print("❌ no passphrase (set AETHER_BACKUP_KEY)")
            sys.exit(1)
        src = Path(args.restore)
        dec = src.with_suffix(".tar.gz")
        engine = decrypt_file(src, dec, pp)
        out_dir = src.parent / "restored"
        out_dir.mkdir(exist_ok=True)
        with tarfile.open(dec) as tar:
            tar.extractall(out_dir)
        dec.unlink()
        print(f"✅ restored [{engine}] → {out_dir}")
        return

    # apply: archive → encrypt → upload
    pp = get_passphrase()
    if not pp:
        print("❌ no passphrase — set AETHER_BACKUP_KEY in .env")
        sys.exit(1)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    tar_path = BACKUP_DIR / f"aether-backup-{stamp}.tar.gz"
    enc_path = BACKUP_DIR / f"aether-backup-{stamp}.tar.gz.enc"

    count = create_archive(tar_path, files)
    engine = encrypt_file(tar_path, enc_path, pp)
    tar_size = tar_path.stat().st_size
    enc_size = enc_path.stat().st_size
    tar_path.unlink()

    result = {
        "stamp": stamp,
        "files": count,
        "archive_mb": round(tar_size / 1024 / 1024, 2),
        "encrypted_mb": round(enc_size / 1024 / 1024, 2),
        "engine": engine,
        "path": str(enc_path),
    }

    if args.apply:
        upload = upload_github(enc_path)
        result["upload"] = upload

    # keep last 5 local
    for old in sorted(BACKUP_DIR.glob("*.enc"))[:-5]:
        old.unlink()

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"✅ backup {stamp}: {count} files, {result['archive_mb']} MB → {result['encrypted_mb']} MB [{engine}]")
        print(f"   {enc_path}")
        if args.apply:
            up = result.get("upload", {})
            print(f"   upload: {'✅ ' + up['where'] if up.get('ok') else '⚠️ ' + up.get('reason','?')}")


if __name__ == "__main__":
    main()
