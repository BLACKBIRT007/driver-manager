"""
config.py - Configuration for Driver Handler by CROD.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP_NAME = "Driver Handler by CROD"
APP_PUBLISHER = "CROD"
APP_REG_NAME = "DriverHandlerByCROD"

GITHUB_OWNER = "BLACKBIRT007"
GITHUB_REPO_NAME = "driver-manager"
GITHUB_REPO = f"{GITHUB_OWNER}/{GITHUB_REPO_NAME}"

LAUNCHER_EXE = "DriverHandlerByCROD.exe"
CORE_EXE = "DriverHandlerByCROD_Core.exe"
INSTALLER_EXE = "Driver_Handler_By_CROD_Setup.exe"


def get_install_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_app_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    else:
        base = Path.home() / ".local" / "share"

    app_dir = base / "DriverHandlerByCROD"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


APP_DIR = get_app_dir()
CONFIG_FILE = APP_DIR / "settings.json"
LOG_FILE = APP_DIR / "driver_handler.log"


def get_version_file_candidates() -> list[Path]:
    candidates = [
        get_install_dir() / "version.txt",
        Path(__file__).resolve().parent / "version.txt",
    ]

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "version.txt")

    return candidates


DEFAULT_CONFIG = {
    "auto_update_drivers": False,
    "auto_update_app": True,
    "check_on_startup": True,
    "check_schedule": "daily",
    "notify_on_update_found": True,
    "notify_on_app_updated": True,
    "start_with_windows": True,
    "excluded_devices": [],
    "auto_update_device_ids": [],
    "last_check": None,
    "last_app_update_check": None,
    "minimize_to_tray": True,
    "theme": "dark",
}


class Config:
    def __init__(self):
        self._data: dict = {}
        self.load()

    def load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._data = {**DEFAULT_CONFIG, **saved}
            except (json.JSONDecodeError, OSError):
                self._data = DEFAULT_CONFIG.copy()
        else:
            self._data = DEFAULT_CONFIG.copy()

        self.save()

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except OSError as e:
            print(f"[Config] Could not save settings: {e}")

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value
        self.save()

    def get_current_app_version(self) -> str:
        for vf in get_version_file_candidates():
            try:
                if vf.exists():
                    content = vf.read_text(encoding="utf-8").strip()
                    if content:
                        return content
            except OSError:
                pass

        return "0.0.0"


config = Config()