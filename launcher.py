"""
launcher.py - Bootstrap entry point.
Checks for updates, then launches the main app.
"""

import sys
import subprocess
import time
from pathlib import Path


def _find_main_app() -> Path:
    here = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent

    candidates = [
        here / "DriverHandlerByCROD.exe",
        here / "DriverManager.exe",
        here / "main_window.py",
    ]

    for c in candidates:
        if c.exists():
            return c

    raise FileNotFoundError("Could not find main app executable.")


def _run_update_check() -> bool:
    try:
        from auto_updater import check_and_update
        updated, msg = check_and_update()
        return updated
    except Exception:
        return False


def main():
    updated = _run_update_check()

    if updated:
        time.sleep(8)
        try:
            exe = Path(sys.executable)
            subprocess.Popen(
                [str(exe)],
                cwd=str(exe.parent),
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception:
            pass
        sys.exit(0)

    try:
        app_path = _find_main_app()

        if app_path.suffix.lower() == ".exe":
            subprocess.Popen(
                [str(app_path)],
                cwd=str(app_path.parent),
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            pythonw = Path(sys.executable).with_name("pythonw.exe")
            py = pythonw if pythonw.exists() else Path(sys.executable)

            subprocess.Popen(
                [str(py), str(app_path)],
                cwd=str(app_path.parent),
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()