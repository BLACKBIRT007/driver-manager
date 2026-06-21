"""
auto_updater.py - Checks GitHub Releases for a newer version of the app itself
and silently downloads + installs it.
"""

from __future__ import annotations
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
import requests
from config import config, GITHUB_REPO
from logger import log

API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
CHECK_INTERVAL_HOURS = 24


def _should_check() -> bool:
    last = config.get("last_app_update_check")
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
        return datetime.now() - last_dt > timedelta(hours=CHECK_INTERVAL_HOURS)
    except ValueError:
        return True


def get_latest_release() -> Tuple[Optional[str], Optional[str]]:
    """
    Queries GitHub API.
    Returns (version_tag, download_url) or (None, None) on failure.
    """
    try:
        resp = requests.get(API_URL, timeout=10, headers={"Accept": "application/vnd.github+json"})
        resp.raise_for_status()
        data = resp.json()
        tag = data.get("tag_name", "").lstrip("v")

        # Find the Setup .exe asset
        url = None
        for asset in data.get("assets", []):
            name: str = asset.get("name", "").lower()
            if name.endswith(".exe") and ("setup" in name or "install" in name):
                url = asset["browser_download_url"]
                break

        return tag or None, url
    except Exception as e:
        log.warning(f"App update check failed: {e}")
        return None, None


def _parse_version(v: str):
    import re
    parts = re.split(r"[.\-]", v.strip())
    result = []
    for p in parts:
        try:
            result.append(int(p))
        except ValueError:
            pass
    return tuple(result)


def is_newer(latest: str, current: str) -> bool:
    return _parse_version(latest) > _parse_version(current)


def download_and_install(download_url: str, new_version: str) -> bool:
    """
    Downloads the new installer and runs it silently.
    The installer (Inno Setup) replaces the app files and then the launcher
    restarts the main exe.
    """
    try:
        log.info(f"Downloading app update v{new_version}…")
        resp = requests.get(download_url, stream=True, timeout=120)
        resp.raise_for_status()

        # Save to a temp file that persists after this process exits
        tmp_dir = Path(tempfile.gettempdir()) / "DriverManagerUpdate"
        tmp_dir.mkdir(exist_ok=True)
        installer_path = tmp_dir / f"DriverManager_Setup_{new_version}.exe"

        with open(installer_path, "wb") as f:
            for chunk in resp.iter_content(65536):
                if chunk:
                    f.write(chunk)

        log.info(f"Launching installer: {installer_path}")
        # /SILENT = Inno Setup silent mode (shows progress), /NORESTART prevents auto-reboot
        subprocess.Popen(
            [str(installer_path), "/SILENT", "/NORESTART"],
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return True
    except Exception as e:
        log.error(f"App self-update failed: {e}")
        return False


def check_and_update(
    notify_callback=None,
    force: bool = False,
) -> Tuple[bool, str]:
    """
    Main entry point called by launcher.py on startup.
    Returns (updated: bool, message: str).
    notify_callback(message) is called when an update is found/installed.
    """
    if not config.get("auto_update_app", True):
        return False, "Auto-update disabled."

    if not force and not _should_check():
        log.debug("App update: skipping check (checked recently).")
        return False, "Checked recently."

    config.set("last_app_update_check", datetime.now().isoformat())

    current_version = config.get_current_app_version()
    log.info(f"Checking for app update (current v{current_version})…")

    latest_version, download_url = get_latest_release()

    if not latest_version:
        return False, "Could not reach GitHub."

    if not is_newer(latest_version, current_version):
        log.info(f"App is up to date (v{current_version}).")
        return False, "Already up to date."

    log.info(f"New app version available: v{latest_version}")

    if not download_url:
        msg = f"App v{latest_version} available but no installer found on GitHub releases."
        log.warning(msg)
        if notify_callback:
            notify_callback(msg)
        return False, msg

    success = download_and_install(download_url, latest_version)
    if success:
        msg = f"Driver Manager updated to v{latest_version}. Restarting…"
        log.info(msg)
        if notify_callback and config.get("notify_on_app_updated", True):
            notify_callback(msg)
        return True, msg
    else:
        return False, "Update download/install failed."


if __name__ == "__main__":
    updated, msg = check_and_update(force=True)
    print(f"Updated: {updated} — {msg}")
