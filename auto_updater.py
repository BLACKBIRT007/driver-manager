"""
auto_updater.py - Self-update from GitHub Releases.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

import requests

from config import config, GITHUB_REPO, INSTALLER_EXE
from logger import log

API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
CHECK_INTERVAL_HOURS = 24


def _creationflags() -> int:
    return subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _should_check() -> bool:
    last = config.get("last_app_update_check")

    if not last:
        return True

    try:
        last_dt = datetime.fromisoformat(last)
        return datetime.now() - last_dt > timedelta(hours=CHECK_INTERVAL_HOURS)
    except ValueError:
        return True


def _parse_version(v: str) -> tuple[int, ...]:
    import re

    result = []

    for part in re.split(r"[.\-]", v.strip().lstrip("v")):
        try:
            result.append(int(part))
        except ValueError:
            pass

    return tuple(result) if result else (0,)


def is_newer(latest: str, current: str) -> bool:
    return _parse_version(latest) > _parse_version(current)


def get_latest_release() -> Tuple[Optional[str], Optional[str]]:
    try:
        resp = requests.get(
            API_URL,
            timeout=15,
            headers={"Accept": "application/vnd.github+json"},
        )
        resp.raise_for_status()

        data = resp.json()
        tag = str(data.get("tag_name", "")).lstrip("v")

        exact_name = INSTALLER_EXE.lower()
        fallback_url = None

        for asset in data.get("assets", []):
            name = str(asset.get("name", "")).lower()
            url = asset.get("browser_download_url")

            if not url:
                continue

            if name == exact_name:
                return tag or None, url

            if name.endswith(".exe") and ("setup" in name or "install" in name):
                fallback_url = url

        return tag or None, fallback_url

    except Exception as e:
        log.warning(f"App update check failed: {e}")
        return None, None


def download_and_install(download_url: str, new_version: str) -> bool:
    try:
        log.info(f"Downloading app update v{new_version}...")

        tmp_dir = Path(tempfile.gettempdir()) / "DriverHandlerByCROD_Update"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        installer_path = tmp_dir / INSTALLER_EXE

        with requests.get(download_url, stream=True, timeout=180) as resp:
            resp.raise_for_status()

            with open(installer_path, "wb") as f:
                for chunk in resp.iter_content(65536):
                    if chunk:
                        f.write(chunk)

        log.info(f"Launching installer: {installer_path}")

        subprocess.Popen(
            [
                str(installer_path),
                "/VERYSILENT",
                "/SUPPRESSMSGBOXES",
                "/NORESTART",
                "/CLOSEAPPLICATIONS",
                "/RESTARTAPPLICATIONS",
            ],
            creationflags=_creationflags(),
        )

        return True

    except Exception as e:
        log.error(f"App self-update failed: {e}")
        return False


def check_and_update(notify_callback=None, force: bool = False) -> Tuple[bool, str]:
    if not config.get("auto_update_app", True):
        return False, "Auto-update disabled."

    if not force and not _should_check():
        return False, "Checked recently."

    config.set("last_app_update_check", datetime.now().isoformat())

    current_version = config.get_current_app_version()
    log.info(f"Checking for app update. Current version: v{current_version}")

    latest_version, download_url = get_latest_release()

    if not latest_version:
        return False, "Could not reach GitHub."

    if not is_newer(latest_version, current_version):
        return False, "Already up to date."

    if not download_url:
        msg = f"App v{latest_version} exists, but no installer asset was found."
        log.warning(msg)

        if notify_callback:
            notify_callback(msg)

        return False, msg

    success = download_and_install(download_url, latest_version)

    if success:
        msg = f"Updating to v{latest_version}."
        log.info(msg)

        if notify_callback and config.get("notify_on_app_updated", True):
            notify_callback(msg)

        return True, msg

    return False, "Update download/install failed."


if __name__ == "__main__":
    updated, msg = check_and_update(force=True)
    print(f"Updated: {updated} - {msg}")