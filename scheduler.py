"""
scheduler.py - Startup registration and background driver scan.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import winreg
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

from config import APP_REG_NAME, LAUNCHER_EXE, config
from logger import log

STARTUP_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _get_launcher_path() -> str:
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).resolve().parent / LAUNCHER_EXE)

    pythonw = Path(sys.executable).with_name("pythonw.exe")
    py = pythonw if pythonw.exists() else Path(sys.executable)
    return f'"{py}" "{Path(__file__).resolve().parent / "launcher.py"}"'


def is_registered_at_startup() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY) as key:
            winreg.QueryValueEx(key, APP_REG_NAME)
        return True
    except FileNotFoundError:
        return False


def register_startup() -> bool:
    try:
        launcher = _get_launcher_path()

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_REG_KEY,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, launcher)

        log.info(f"Registered startup: {launcher}")
        config.set("start_with_windows", True)
        return True

    except Exception as e:
        log.error(f"Failed to register startup: {e}")
        return False


def unregister_startup() -> bool:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_REG_KEY,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            winreg.DeleteValue(key, APP_REG_NAME)

        log.info("Removed from startup.")
        config.set("start_with_windows", False)
        return True

    except FileNotFoundError:
        return True
    except Exception as e:
        log.error(f"Failed to remove startup entry: {e}")
        return False


def _should_scan_now() -> bool:
    schedule = config.get("check_schedule", "daily")
    last = config.get("last_check")

    if not last:
        return True

    try:
        last_dt = datetime.fromisoformat(last)
    except ValueError:
        return True

    thresholds = {
        "startup": timedelta(0),
        "daily": timedelta(days=1),
        "weekly": timedelta(weeks=1),
    }

    return datetime.now() - last_dt >= thresholds.get(schedule, timedelta(days=1))


def run_background_scan(
    on_updates_found: Optional[Callable[[list], None]] = None,
    on_scan_done: Optional[Callable[[list], None]] = None,
):
    def _worker():
        if not _should_scan_now() and not config.get("check_on_startup", True):
            log.debug("Background scan skipped.")
            return

        log.info("Background scan starting.")
        config.set("last_check", datetime.now().isoformat())

        from device_scanner import scan_devices
        from driver_checker import check_all_devices
        from driver_installer import install_devices_threaded, InstallResult

        excluded = config.get("excluded_devices", [])
        devices = scan_devices(exclude_ids=excluded)
        devices = check_all_devices(devices)

        updates = [d for d in devices if d.update_available]

        if on_scan_done:
            on_scan_done(devices)

        if not updates:
            log.info("Background scan: no driver updates found.")
            return

        log.info(f"Background scan: {len(updates)} update(s) found.")

        if on_updates_found:
            on_updates_found(updates)

        if config.get("auto_update_drivers", False):
            auto_ids = set(config.get("auto_update_device_ids", []))
            to_install = [d for d in updates if not auto_ids or d.device_id in auto_ids]

            if to_install:
                log.info(f"Auto-installing {len(to_install)} driver(s).")
                results: list[InstallResult] = []

                def collect(r):
                    results.append(r)

                t = install_devices_threaded(to_install, on_result=collect)
                t.join()

                ok = sum(1 for r in results if r.success)
                log.info(f"Auto-install complete: {ok}/{len(to_install)} succeeded.")

    thread = threading.Thread(target=_worker, daemon=True, name="BackgroundScan")
    thread.start()
    return thread