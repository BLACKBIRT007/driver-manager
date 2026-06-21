"""
launcher.py - Bootstrap entry point. Runs on Windows startup.
1. Checks for and applies app self-update
2. Launches the main DriverManager app
This file is intentionally tiny and stable — it almost never needs updating.
"""

import os
import sys
import subprocess
import time
from pathlib import Path


def _find_main_app() -> Path:
    """Finds DriverManager.exe relative to this launcher."""
    here = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    candidates = [
        here / "DriverManager.exe",
        here / "DriverManager" / "DriverManager.exe",
        here / "main_window.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError("Could not find DriverManager.exe")


def _run_update_check():
    """Imports and runs auto_updater in a subprocess-safe way."""
    try:
        # When frozen (PyInstaller), auto_updater is bundled inside
        from auto_updater import check_and_update
        updated, msg = check_and_update()
        return updated
    except ImportError:
        return False
    except Exception as e:
        print(f"[Launcher] Update check error: {e}")
        return False


def main():
    print("[Launcher] Driver Manager Launcher starting…")

    updated = _run_update_check()

    if updated:
        # Installer is running in background — give it a moment then restart
        print("[Launcher] Update applied, waiting for installer to finish…")
        time.sleep(8)
        # Re-launch this launcher (which will now run the new version)
        try:
            exe = Path(sys.executable)
            subprocess.Popen([str(exe)], cwd=str(exe.parent))
        except Exception as e:
            print(f"[Launcher] Restart failed: {e}")
        sys.exit(0)

    # Launch the main app
    try:
        app_path = _find_main_app()
        print(f"[Launcher] Starting: {app_path}")

        if app_path.suffix == ".exe":
            subprocess.Popen([str(app_path)], cwd=str(app_path.parent))
        else:
            # Development mode — run as Python script
            subprocess.Popen([sys.executable, str(app_path)], cwd=str(app_path.parent))

    except FileNotFoundError as e:
        print(f"[Launcher] ERROR: {e}")
        input("Press Enter to exit…")
        sys.exit(1)


if __name__ == "__main__":
    main()
