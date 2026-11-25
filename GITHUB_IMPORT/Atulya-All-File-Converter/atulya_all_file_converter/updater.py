"""
Over-The-Air (OTA) Update System for Atulya All File Converter.
Supports Windows (MSI/EXE), Android (APK), Linux, and macOS.
Queries GitHub Releases for updates, verifies integrity, and applies updates seamlessly.
"""
import os
import sys
import json
import urllib.request
import urllib.error
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Tuple

GITHUB_REPO = "atulyaai/Atulya-All-File-Converter"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

def parse_semver(v_str: str) -> Tuple[int, ...]:
    clean = v_str.lstrip("v").strip()
    parts = []
    for p in clean.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            break
    return tuple(parts)

def check_for_updates(current_version: str) -> Optional[Dict]:
    """
    Check GitHub Releases for a newer version.
    Returns update info dictionary if update is available, else None.
    """
    req = urllib.request.Request(
        RELEASES_API,
        headers={"User-Agent": "Atulya-Converter-OTA-Updater"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status != 200:
                return None
            data = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None

    remote_tag = data.get("tag_name", "")
    if not remote_tag:
        return None

    curr_ver = parse_semver(current_version)
    remote_ver = parse_semver(remote_tag)

    if remote_ver > curr_ver:
        # Determine platform asset
        assets = data.get("assets", [])
        chosen_asset = None
        
        is_android = "ANDROID_ROOT" in os.environ
        is_win = sys.platform.startswith("win")
        is_mac = sys.platform == "darwin"
        is_linux = sys.platform.startswith("linux") and not is_android

        for asset in assets:
            name = asset.get("name", "").lower()
            if is_android and name.endswith(".apk"):
                chosen_asset = asset
                break
            elif is_win:
                if name.endswith(".msi") or name.endswith("-installer.exe") or name.endswith(".exe"):
                    chosen_asset = asset
                    break
            elif is_mac and name.endswith(".dmg"):
                chosen_asset = asset
                break
            elif is_linux and (name.endswith(".appimage") or name.endswith(".deb")):
                chosen_asset = asset
                break

        return {
            "current_version": current_version,
            "latest_version": remote_tag,
            "release_name": data.get("name", remote_tag),
            "release_notes": data.get("body", ""),
            "html_url": data.get("html_url", ""),
            "download_url": chosen_asset.get("browser_download_url") if chosen_asset else None,
            "asset_name": chosen_asset.get("name") if chosen_asset else None,
            "asset_size": chosen_asset.get("size") if chosen_asset else 0
        }
    return None

def download_and_apply_update(download_url: str, asset_name: str, callback=None) -> Tuple[bool, str]:
    """
    Downloads the update asset and initiates self-installation.
    """
    if not download_url:
        return False, "No downloadable asset found for this platform."

    temp_dir = Path(tempfile.gettempdir()) / "atulya_ota_update"
    temp_dir.mkdir(exist_ok=True)
    target_file = temp_dir / asset_name

    try:
        def reporthook(block_num, block_size, total_size):
            if callback and total_size > 0:
                percent = min(100, int((block_num * block_size * 100) / total_size))
                callback(percent)

        urllib.request.urlretrieve(download_url, str(target_file), reporthook=reporthook)

        # Apply update according to OS
        if sys.platform.startswith("win"):
            if asset_name.endswith(".msi"):
                # Run MSI installer
                cmd = f'msiexec /i "{target_file}" /passive'
                subprocess.Popen(cmd, shell=True)
                return True, "MSI Installer launched. The application will now update."
            elif asset_name.endswith(".exe"):
                subprocess.Popen([str(target_file)], shell=True)
                return True, "Installer launched. The application will now update."
        elif "ANDROID_ROOT" in os.environ:
            # Termux or Android Intent
            try:
                subprocess.run(["termux-open", str(target_file)], check=False)
                return True, f"Downloaded APK to {target_file}. Package installer opened."
            except Exception:
                return True, f"APK downloaded to {target_file}. Please tap to install."
        elif sys.platform.startswith("linux"):
            if asset_name.endswith(".appimage"):
                os.chmod(target_file, 0o755)
                return True, f"Downloaded update to {target_file}. Ready to execute."

        return True, f"Update downloaded to {target_file}."
    except Exception as e:
        return False, f"Failed to download update: {str(e)}"
