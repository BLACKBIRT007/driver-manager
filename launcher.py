"""
launcher.py - Visible app launcher/updater.

Users run DriverHandlerByCROD.exe.
It checks for app updates, then launches DriverHandlerByCROD_Core.exe.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _creationflags() -> int:
    return subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _find_core_app() -> Path:
    here = _base_dir()

    candidates = [
        here / "DriverHandlerByCROD_Core.exe",
        here / "main_window.py",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError("Could not find DriverHandlerByCROD_Core.exe or main_window.py.")


def _run_update_check() -> bool:
    try:
        from auto_updater import check_and_update

        updated, _message = check_and_update()
        return updated
    except Exception:
        return False


def _start_core_app():
    app_path = _find_core_app()

    if app_path.suffix.lower() == ".exe":
        subprocess.Popen(
            [str(app_path)],
            cwd=str(app_path.parent),
            creationflags=_creationflags(),
        )
        return

    pythonw = Path(sys.executable).with_name("pythonw.exe")
    py = pythonw if pythonw.exists() else Path(sys.executable)

    subprocess.Popen(
        [str(py), str(app_path)],
        cwd=str(app_path.parent),
        creationflags=_creationflags(),
    )


def main():
    updated = _run_update_check()

    if updated:
        # Installer has been started. Exit so files are not locked.
        sys.exit(0)

    try:
        _start_core_app()
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()