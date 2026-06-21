"""
config.py - Configuration management for Driver Update Manager
Handles reading/writing settings to a JSON file.
"""

import json
import os
import sys
from pathlib import Path


def get_app_dir() -> Path:
    """Returns the directory where config/logs are stored (AppData/Local)."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    else:
        base = Path.home() / ".local" / "share"
    app_dir = base / "DriverUpdateManager"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


APP_DIR = get_app_dir()
CONFIG_FILE = APP_DIR / "settings.json"
LOG_FILE = APP_DIR / "driver_manager.log"
VERSION_FILE = Path(__file__).parent / "version.txt"
GITHUB_REPO = "BLACKBIRT007/driver-manager"   # ← change this to your GitHub repo

DEFAULT_CONFIG = {
    "auto_update_drivers": False,          # silently install driver updates
    "auto_update_app": True,               # self-update the app on startup
    "check_on_startup": True,              # scan for driver updates on startup
    "check_schedule": "daily",             # "startup" | "daily" | "weekly"
    "notify_on_update_found": True,        # tray notification when updates found
    "notify_on_app_updated": True,         # tray notification after self-update
    "start_with_windows": True,
    "excluded_devices": [],                # list of device IDs to skip
    "auto_update_device_ids": [],          # devices approved for silent update
    "last_check": None,
    "last_app_update_check": None,
    "minimize_to_tray": True,
    "theme": "dark",                       # "dark" | "light"
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
        try:
            return VERSION_FILE.read_text(encoding="utf-8").strip()
        except OSError:
            return "0.0.0"


# Singleton instance used by all modules
config = Config()
