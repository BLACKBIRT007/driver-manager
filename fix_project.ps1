$ErrorActionPreference = "Stop"

if (!(Test-Path "main_window.py")) {
    throw "Run this inside the root of your driver-manager repo. main_window.py was not found."
}

$BackupDir = ".backup_ai_fix_$(Get-Date -Format yyyyMMdd_HHmmss)"

function Write-Text {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][string]$Text
    )

    $FullPath = Join-Path $PWD $Path
    $Dir = Split-Path -Parent $FullPath

    if ($Dir -and !(Test-Path $Dir)) {
        New-Item -ItemType Directory -Force -Path $Dir | Out-Null
    }

    [System.IO.File]::WriteAllText(
        $FullPath,
        $Text,
        [System.Text.UTF8Encoding]::new($false)
    )
}

function Backup-ItemSafe {
    param([string]$Path)

    if (Test-Path $Path) {
        $Dest = Join-Path $BackupDir $Path
        $DestDir = Split-Path -Parent $Dest

        if ($DestDir -and !(Test-Path $DestDir)) {
            New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
        }

        Copy-Item $Path $Dest -Force
    }
}

Write-Host "[fix] Backing up current files to $BackupDir"
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null

$FilesToBackup = @(
    "README.md",
    "index.html",
    "build.bat",
    "requirements.txt",
    "version.txt",
    "launcher.py",
    "auto_updater.py",
    "config.py",
    "scheduler.py",
    "driver_checker.py",
    "driver_installer.py",
    "release.yml",
    "installer.iss",
    ".github\workflows\release.yml",
    "setup_builder\installer.iss",
    ".gitignore"
)

foreach ($File in $FilesToBackup) {
    Backup-ItemSafe $File
}

Write-Host "[fix] Creating correct folders"
New-Item -ItemType Directory -Force -Path ".github\workflows" | Out-Null
New-Item -ItemType Directory -Force -Path "setup_builder" | Out-Null
New-Item -ItemType Directory -Force -Path "release" | Out-Null

Write-Host "[fix] Removing wrong root workflow/installer files if present"
if (Test-Path "release.yml") { Remove-Item "release.yml" -Force }
if (Test-Path "installer.iss") { Remove-Item "installer.iss" -Force }

Write-Host "[fix] Removing Python cache from repo"
Get-ChildItem -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

if (!(Test-Path "version.txt")) {
    Write-Text "version.txt" "1.0.0`n"
}

Write-Host "[fix] Writing .gitignore"
Write-Text ".gitignore" @'
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.venv/
venv/
env/

# Build output
build/
dist/
release/
*.spec

# Logs / local data
*.log
*.tmp

# Local backups
.backup_ai_fix_*/

# OS / editor
.DS_Store
Thumbs.db
.vscode/
.idea/
'@

Write-Host "[fix] Writing requirements.txt"
Write-Text "requirements.txt" @'
PyQt6>=6.6.0
requests>=2.31.0
wmi>=1.5.1
pywin32>=306
pystray>=0.19.5
Pillow>=10.0.0
pyinstaller>=6.3.0
'@

Write-Host "[fix] Writing config.py"
Write-Text "config.py" @'
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
'@

Write-Host "[fix] Writing launcher.py"
Write-Text "launcher.py" @'
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
'@

Write-Host "[fix] Writing auto_updater.py"
Write-Text "auto_updater.py" @'
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
'@

Write-Host "[fix] Writing scheduler.py"
Write-Text "scheduler.py" @'
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
'@

Write-Host "[fix] Writing safer driver_checker.py"
Write-Text "driver_checker.py" @'
"""
driver_checker.py - Checks Microsoft Update Catalog for possible newer drivers.

This is still experimental. Driver matching must be reviewed manually.
"""

from __future__ import annotations

import html
import json
import re
import time
from typing import List, Optional, Tuple

import requests

from device_scanner import Device
from logger import log

CATALOG_SEARCH_URL = "https://www.catalog.update.microsoft.com/Search.aspx"
CATALOG_DOWNLOAD_URL = "https://www.catalog.update.microsoft.com/DownloadDialog.aspx"
REQUEST_TIMEOUT = 20
RATE_LIMIT_DELAY = 0.35


def _parse_version(version_str: str) -> Tuple[int, ...]:
    if not version_str:
        return (0,)

    parts = re.split(r"[.\-,_ ]", version_str.strip())
    result = []

    for part in parts:
        try:
            result.append(int(part))
        except ValueError:
            pass

    return tuple(result) if result else (0,)


def _version_is_newer(latest: str, current: str) -> bool:
    return _parse_version(latest) > _parse_version(current)


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )
    return s


def _extract_update_ids(text: str) -> list[str]:
    ids = re.findall(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        text,
    )

    seen = set()
    out = []

    for item in ids:
        item = item.lower()

        if item not in seen:
            seen.add(item)
            out.append(item)

    return out


def _extract_versions(text: str) -> list[str]:
    versions = re.findall(r"\b\d+\.\d+(?:\.\d+){0,4}\b", text)
    return sorted(set(versions), key=_parse_version, reverse=True)


def _get_direct_download_url(session: requests.Session, update_id: str) -> Optional[str]:
    try:
        payload = {
            "updateIDs": json.dumps(
                [
                    {
                        "size": 0,
                        "languages": "",
                        "uidInfo": update_id,
                        "updateID": update_id,
                    }
                ]
            )
        }

        resp = session.post(CATALOG_DOWNLOAD_URL, data=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()

        text = html.unescape(resp.text)
        text = text.replace("\\/", "/").replace("\\u0026", "&")

        urls = re.findall(
            r"https?://download\.windowsupdate\.com/[^\"'<>\\\s]+",
            text,
            flags=re.IGNORECASE,
        )

        for url in urls:
            lower = url.lower()

            if any(ext in lower for ext in (".cab", ".msu", ".zip", ".exe", ".msi")):
                return url

        return urls[0] if urls else None

    except Exception as e:
        log.debug(f"Could not get direct Catalog download URL for {update_id}: {e}")
        return None


def _search_catalog(query: str) -> Optional[dict]:
    try:
        session = _session()

        resp = session.get(
            CATALOG_SEARCH_URL,
            params={"q": query},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()

        versions = _extract_versions(resp.text)
        update_ids = _extract_update_ids(resp.text)

        if not versions and not update_ids:
            return None

        best_version = versions[0] if versions else None
        download_url = None

        for update_id in update_ids[:8]:
            download_url = _get_direct_download_url(session, update_id)

            if download_url:
                break

        return {
            "version": best_version,
            "download_url": download_url,
        }

    except requests.RequestException as e:
        log.debug(f"Catalog request failed for '{query}': {e}")
        return None


def check_device(device: Device) -> Device:
    if not device.driver_version:
        return device

    query_parts = []

    if device.manufacturer and device.manufacturer.lower() not in ("microsoft", "(standard", ""):
        query_parts.append(device.manufacturer)

    query_parts.append(device.display_name)
    query_parts.append("driver")

    query = " ".join(query_parts)

    log.debug(f"Checking driver for: {device.display_name} current={device.driver_version}")

    result = _search_catalog(query)

    if result and result.get("version"):
        latest = result["version"]

        if _version_is_newer(latest, device.driver_version):
            device.latest_version = latest
            device.update_available = True
            device.download_url = result.get("download_url")
            log.info(f"Possible update found: {device.display_name} {device.driver_version} -> {latest}")
        else:
            device.latest_version = device.driver_version
            device.update_available = False
    else:
        device.latest_version = None
        device.update_available = False

    return device


def check_all_devices(devices: List[Device], progress_callback=None) -> List[Device]:
    total = len(devices)
    log.info(f"Checking {total} devices for driver updates.")

    for i, device in enumerate(devices):
        try:
            check_device(device)
        except Exception as e:
            log.error(f"Error checking {device.display_name}: {e}")
        finally:
            time.sleep(RATE_LIMIT_DELAY)

            if progress_callback:
                progress_callback(i + 1, total)

    updates_found = sum(1 for d in devices if d.update_available)
    log.info(f"Driver check complete. {updates_found} possible update(s) available.")

    return devices


if __name__ == "__main__":
    from device_scanner import scan_devices

    devices = scan_devices()
    checked = check_all_devices(devices, progress_callback=lambda c, t: print(f"{c}/{t}"))

    for d in checked:
        status = f"-> {d.latest_version}" if d.update_available else "up to date"
        print(f"{d.display_name:70s} | {d.driver_version:20s} | {status}")
'@

Write-Host "[fix] Writing safer driver_installer.py"
Write-Text "driver_installer.py" @'
"""
driver_installer.py - Downloads and installs driver packages.

Supports .cab, .zip, .inf, .msu, .exe and .msi.
Run as Administrator for driver installs.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Callable, Optional, Tuple
from urllib.parse import unquote, urlparse

import requests

from device_scanner import Device
from logger import log

DOWNLOAD_TIMEOUT = 180


class InstallResult:
    def __init__(self, device: Device, success: bool, message: str = ""):
        self.device = device
        self.success = success
        self.message = message

    def __repr__(self):
        status = "OK" if self.success else "FAILED"
        return f"<InstallResult {status}: {self.device.display_name} - {self.message}>"


def _creationflags() -> int:
    return subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def _is_admin() -> bool:
    if os.name != "nt":
        return True

    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _filename_from_url(url: str) -> str:
    path = unquote(urlparse(url).path)
    name = Path(path).name

    if name:
        return name

    return "driver_package.cab"


def _looks_like_html(path: Path) -> bool:
    try:
        head = path.read_bytes()[:512].lower()
        return b"<html" in head or b"<!doctype html" in head
    except OSError:
        return False


def _download_file(
    url: str,
    dest: Path,
    progress: Optional[Callable[[int, int], None]] = None,
) -> bool:
    try:
        with requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT) as response:
            response.raise_for_status()

            total = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(dest, "wb") as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if progress and total:
                            progress(downloaded, total)

        log.info(f"Downloaded {dest.name} ({downloaded:,} bytes)")
        return True

    except Exception as e:
        log.error(f"Download failed for {url}: {e}")
        return False


def _run(cmd: list[str], timeout: int = 300) -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=_creationflags(),
        )

        output = (result.stdout or "") + "\n" + (result.stderr or "")
        output = output.strip()

        if result.returncode in (0, 3010, 1641):
            msg = output or "OK"

            if result.returncode == 3010:
                msg += " Reboot required."

            return True, msg

        return False, output or f"Command failed with code {result.returncode}"

    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def _install_inf(inf_path: Path) -> Tuple[bool, str]:
    return _run(["pnputil", "/add-driver", str(inf_path), "/install"], timeout=180)


def _install_inf_tree(folder: Path) -> Tuple[bool, str]:
    infs = list(folder.rglob("*.inf"))

    if not infs:
        return False, "No .inf file found in extracted package."

    best_message = ""

    for inf in infs:
        success, msg = _install_inf(inf)
        best_message = msg

        if success:
            return True, msg

    return False, best_message or "No INF install succeeded."


def _extract_cab(cab_path: Path, out_dir: Path) -> Tuple[bool, str]:
    return _run(["expand", "-F:*", str(cab_path), str(out_dir)], timeout=180)


def _install_cab(cab_path: Path, work_dir: Path) -> Tuple[bool, str]:
    extracted = work_dir / "cab_extracted"
    extracted.mkdir(parents=True, exist_ok=True)

    ok, msg = _extract_cab(cab_path, extracted)

    if not ok:
        return False, f"CAB extract failed: {msg}"

    return _install_inf_tree(extracted)


def _install_zip(zip_path: Path, work_dir: Path) -> Tuple[bool, str]:
    import zipfile

    extracted = work_dir / "zip_extracted"
    extracted.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extracted)

    return _install_inf_tree(extracted)


def _install_msu(msu_path: Path) -> Tuple[bool, str]:
    return _run(["wusa.exe", str(msu_path), "/quiet", "/norestart"], timeout=600)


def _install_msi(msi_path: Path) -> Tuple[bool, str]:
    return _run(["msiexec.exe", "/i", str(msi_path), "/qn", "/norestart"], timeout=600)


def _install_exe(exe_path: Path) -> Tuple[bool, str]:
    silent_args = [
        ["/S"],
        ["/s"],
        ["/quiet"],
        ["/q"],
        ["/SILENT"],
        ["/VERYSILENT"],
        ["/install", "/quiet", "/norestart"],
    ]

    last_msg = "No silent flag worked."

    for args in silent_args:
        success, msg = _run([str(exe_path), *args], timeout=600)
        last_msg = msg

        if success:
            return True, f"Installed with {' '.join(args)}"

    return False, last_msg


def install_device_driver(
    device: Device,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> InstallResult:
    if not _is_admin():
        return InstallResult(device, False, "Run the app as Administrator to install drivers.")

    if not device.download_url:
        try:
            if progress_callback:
                progress_callback("No direct package URL. Triggering Windows Update scan.")

            subprocess.run(
                ["usoclient", "StartScan"],
                timeout=10,
                capture_output=True,
                creationflags=_creationflags(),
            )
        except Exception:
            pass

        return InstallResult(
            device,
            False,
            "No direct Catalog package URL was found. Windows Update scan was triggered instead.",
        )

    with tempfile.TemporaryDirectory(prefix="driver_handler_") as tmp:
        tmp_dir = Path(tmp)
        filename = _filename_from_url(device.download_url)
        dest = tmp_dir / filename

        if progress_callback:
            progress_callback(f"Downloading {filename}...")

        ok = _download_file(device.download_url, dest)

        if not ok:
            return InstallResult(device, False, "Download failed.")

        if _looks_like_html(dest):
            return InstallResult(
                device,
                False,
                "Downloaded HTML instead of a driver package. Catalog link was not a direct package URL.",
            )

        if progress_callback:
            progress_callback("Installing...")

        suffix = dest.suffix.lower()

        if suffix == ".inf":
            success, msg = _install_inf(dest)
        elif suffix == ".cab":
            success, msg = _install_cab(dest, tmp_dir)
        elif suffix == ".zip":
            success, msg = _install_zip(dest, tmp_dir)
        elif suffix == ".msu":
            success, msg = _install_msu(dest)
        elif suffix == ".msi":
            success, msg = _install_msi(dest)
        elif suffix == ".exe":
            success, msg = _install_exe(dest)
        else:
            success, msg = False, f"Unsupported package type: {suffix or 'unknown'}"

        log.info(f"Install {device.display_name}: {'OK' if success else 'FAILED'} - {msg}")
        return InstallResult(device, success, msg)


def install_devices_threaded(
    devices: list,
    on_result: Callable[[InstallResult], None],
    on_progress: Optional[Callable[[str, int, int], None]] = None,
):
    def _worker():
        total = len(devices)

        for i, device in enumerate(devices):
            if on_progress:
                on_progress(f"Installing {device.display_name}...", i, total)

            result = install_device_driver(
                device,
                progress_callback=lambda s: on_progress(s, i, total) if on_progress else None,
            )

            on_result(result)

        if on_progress:
            on_progress("All installations complete.", total, total)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return t
'@

Write-Host "[fix] Writing build.bat"
Write-Text "build.bat" @'
@echo off
setlocal enabledelayedexpansion

echo.
echo ============================================
echo Driver Handler by CROD - Build
echo ============================================
echo.

if not exist version.txt (
    echo 1.0.0>version.txt
)

for /f "usebackq delims=" %%v in ("version.txt") do set APP_VERSION=%%v

echo Version: %APP_VERSION%
echo.

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if not exist release mkdir release

echo.
echo [1/3] Building core app...
python -m PyInstaller --noconfirm --onefile --noconsole --clean ^
  --name "DriverHandlerByCROD_Core" ^
  --add-data "version.txt;." ^
  --hidden-import "wmi" ^
  --hidden-import "win32api" ^
  --hidden-import "win32con" ^
  --hidden-import "winreg" ^
  --hidden-import "pystray" ^
  --hidden-import "PIL" ^
  main_window.py

if errorlevel 1 (
    echo [ERROR] Core app build failed.
    exit /b 1
)

echo.
echo [2/3] Building visible launcher...
python -m PyInstaller --noconfirm --onefile --noconsole --clean ^
  --name "DriverHandlerByCROD" ^
  --add-data "version.txt;." ^
  --hidden-import "auto_updater" ^
  --hidden-import "config" ^
  --hidden-import "logger" ^
  launcher.py

if errorlevel 1 (
    echo [ERROR] Launcher build failed.
    exit /b 1
)

copy /y "dist\DriverHandlerByCROD_Core.exe" "release\DriverHandlerByCROD_Core.exe" >nul
copy /y "dist\DriverHandlerByCROD.exe" "release\DriverHandlerByCROD.exe" >nul
copy /y "version.txt" "release\version.txt" >nul

echo.
echo [3/3] Building installer if Inno Setup exists...

set ISCC=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set ISCC=C:\Program Files\Inno Setup 6\ISCC.exe

if "%ISCC%"=="" (
    echo WARNING: Inno Setup was not found.
    echo Install Inno Setup 6 to build Driver_Handler_By_CROD_Setup.exe
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "(Get-Content 'setup_builder\installer.iss' -Raw) -replace '#define MyAppVersion \"[^\"]+\"', '#define MyAppVersion \"%APP_VERSION%\"' | Set-Content 'setup_builder\installer_build.iss' -Encoding UTF8"
    "%ISCC%" "setup_builder\installer_build.iss"
)

echo.
echo ============================================
echo Build done.
echo Output folder: release
echo Expected:
echo - DriverHandlerByCROD.exe
echo - DriverHandlerByCROD_Core.exe
echo - Driver_Handler_By_CROD_Setup.exe
echo ============================================
echo.

endlocal
'@

Write-Host "[fix] Writing Inno Setup installer"
Write-Text "setup_builder\installer.iss" @'
; Driver Handler by CROD - Inno Setup script

#define MyAppName "Driver Handler by CROD"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "CROD"
#define MyAppURL "https://github.com/BLACKBIRT007/driver-manager"
#define MyAppExeName "DriverHandlerByCROD.exe"
#define MyAppCoreExeName "DriverHandlerByCROD_Core.exe"
#define MyAppSetupName "Driver_Handler_By_CROD_Setup"

[Setup]
AppId={{73DDA837-870E-4D67-99AE-C4A2E928044D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=..\release
OutputBaseFilename={#MyAppSetupName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked
Name: "startupentry"; Description: "Start with Windows"; GroupDescription: "Startup:"; Flags: checked

[Files]
Source: "..\release\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\release\{#MyAppCoreExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\release\version.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "DriverHandlerByCROD"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: startupentry

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "reg"; Parameters: "delete ""HKCU\Software\Microsoft\Windows\CurrentVersion\Run"" /v DriverUpdateManager /f"; Flags: runhidden
Filename: "reg"; Parameters: "delete ""HKCU\Software\Microsoft\Windows\CurrentVersion\Run"" /v DriverHandlerByCROD /f"; Flags: runhidden
'@

Write-Host "[fix] Writing GitHub Actions workflow"
Write-Text ".github\workflows\release.yml" @'
name: Release

on:
  push:
    tags:
      - "v*.*.*"
  workflow_dispatch:
    inputs:
      version:
        description: "Version number, example: 1.0.1"
        required: false
        type: string

permissions:
  contents: write

jobs:
  build:
    runs-on: windows-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Resolve version
        shell: pwsh
        run: |
          if ("${{ github.event_name }}" -eq "workflow_dispatch" -and "${{ inputs.version }}" -ne "") {
            $version = "${{ inputs.version }}"
          } elseif ("${{ github.ref_type }}" -eq "tag") {
            $version = "${{ github.ref_name }}" -replace "^v", ""
          } elseif (Test-Path version.txt) {
            $version = (Get-Content version.txt -Raw).Trim()
          } else {
            $version = "1.0.0"
          }

          Set-Content -Path version.txt -Value $version
          "APP_VERSION=$version" | Out-File -FilePath $env:GITHUB_ENV -Append
          "RELEASE_TAG=v$version" | Out-File -FilePath $env:GITHUB_ENV -Append
          Write-Host "Version: $version"

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install Python dependencies
        shell: pwsh
        run: |
          python -m pip install --upgrade pip
          python -m pip install -r requirements.txt

      - name: Build core EXE
        shell: pwsh
        run: |
          python -m PyInstaller --noconfirm --onefile --noconsole --clean `
            --name "DriverHandlerByCROD_Core" `
            --add-data "version.txt;." `
            --hidden-import "wmi" `
            --hidden-import "win32api" `
            --hidden-import "win32con" `
            --hidden-import "winreg" `
            --hidden-import "pystray" `
            --hidden-import "PIL" `
            main_window.py

      - name: Build visible launcher EXE
        shell: pwsh
        run: |
          python -m PyInstaller --noconfirm --onefile --noconsole --clean `
            --name "DriverHandlerByCROD" `
            --add-data "version.txt;." `
            --hidden-import "auto_updater" `
            --hidden-import "config" `
            --hidden-import "logger" `
            launcher.py

      - name: Prepare release folder
        shell: pwsh
        run: |
          New-Item -ItemType Directory -Force -Path release | Out-Null
          Copy-Item dist\DriverHandlerByCROD_Core.exe release\DriverHandlerByCROD_Core.exe -Force
          Copy-Item dist\DriverHandlerByCROD.exe release\DriverHandlerByCROD.exe -Force
          Copy-Item version.txt release\version.txt -Force

      - name: Install Inno Setup
        shell: pwsh
        run: choco install innosetup -y --no-progress

      - name: Build installer
        shell: pwsh
        run: |
          (Get-Content "setup_builder\installer.iss" -Raw) `
            -replace '#define MyAppVersion "[^"]+"', "#define MyAppVersion `"$env:APP_VERSION`"" |
            Set-Content "setup_builder\installer_build.iss" -Encoding UTF8

          & "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" "setup_builder\installer_build.iss"

          if (!(Test-Path "release\Driver_Handler_By_CROD_Setup.exe")) {
            throw "Installer was not created."
          }

      - name: Upload release assets
        uses: softprops/action-gh-release@v2
        with:
          tag_name: ${{ env.RELEASE_TAG }}
          name: Driver Handler by CROD ${{ env.APP_VERSION }}
          generate_release_notes: true
          files: |
            release\Driver_Handler_By_CROD_Setup.exe
            release\DriverHandlerByCROD.exe
            release\DriverHandlerByCROD_Core.exe
            release\version.txt
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
'@

Write-Host "[fix] Writing index.html"
Write-Text "index.html" @'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Driver Handler by CROD</title>
  <style>
    :root {
      --bg: #070b16;
      --panel: #0e1629;
      --panel-2: #111d35;
      --text: #eef4ff;
      --muted: #9fb0d0;
      --blue: #4f7cff;
      --blue-2: #7fa0ff;
      --border: #243454;
      --warn: #ffd166;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(79,124,255,.35), transparent 35%),
        radial-gradient(circle at bottom right, rgba(127,160,255,.16), transparent 40%),
        var(--bg);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.5;
    }

    header {
      max-width: 1100px;
      margin: 0 auto;
      padding: 32px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
    }

    .logo {
      font-weight: 800;
      letter-spacing: .3px;
      font-size: 18px;
    }

    nav a {
      color: var(--muted);
      text-decoration: none;
      margin-left: 18px;
      font-size: 14px;
    }

    nav a:hover {
      color: var(--text);
    }

    .hero {
      max-width: 1100px;
      margin: 0 auto;
      padding: 56px 20px 36px;
      display: grid;
      grid-template-columns: 1.1fr .9fr;
      gap: 32px;
      align-items: center;
    }

    .badge {
      display: inline-block;
      padding: 8px 12px;
      background: rgba(79,124,255,.14);
      border: 1px solid var(--border);
      border-radius: 999px;
      color: var(--blue-2);
      font-weight: 700;
      font-size: 13px;
      margin-bottom: 18px;
    }

    h1 {
      font-size: clamp(38px, 6vw, 68px);
      line-height: .96;
      margin: 0 0 20px;
      letter-spacing: -2px;
    }

    .lead {
      color: var(--muted);
      font-size: 18px;
      max-width: 640px;
      margin-bottom: 26px;
    }

    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 18px;
    }

    .btn {
      display: inline-block;
      padding: 13px 20px;
      border-radius: 10px;
      text-decoration: none;
      font-weight: 800;
      border: 1px solid var(--border);
    }

    .btn.primary {
      background: var(--blue);
      color: white;
      border-color: var(--blue);
      box-shadow: 0 12px 40px rgba(79,124,255,.28);
    }

    .btn.secondary {
      background: var(--panel-2);
      color: var(--text);
    }

    .small {
      color: var(--muted);
      font-size: 13px;
    }

    .mock {
      background: rgba(14,22,41,.88);
      border: 1px solid var(--border);
      border-radius: 18px;
      overflow: hidden;
      box-shadow: 0 20px 80px rgba(0,0,0,.35);
    }

    .mock-head {
      padding: 14px 16px;
      background: #0a1020;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      color: var(--muted);
      font-size: 13px;
    }

    .mock-body {
      padding: 16px;
    }

    .mock-row {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      padding: 12px;
      border: 1px solid var(--border);
      border-radius: 12px;
      margin-bottom: 10px;
      background: rgba(255,255,255,.02);
    }

    .mock-row strong {
      display: block;
      margin-bottom: 4px;
    }

    .status {
      color: var(--warn);
      font-weight: 800;
    }

    section {
      max-width: 1100px;
      margin: 0 auto;
      padding: 36px 20px;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
    }

    .card {
      background: rgba(14,22,41,.8);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 20px;
    }

    .card h3 {
      margin-top: 0;
    }

    .card p {
      color: var(--muted);
      margin-bottom: 0;
    }

    footer {
      max-width: 1100px;
      margin: 0 auto;
      padding: 32px 20px 52px;
      color: var(--muted);
      font-size: 13px;
    }

    @media (max-width: 850px) {
      .hero,
      .grid {
        grid-template-columns: 1fr;
      }

      nav {
        display: none;
      }
    }
  </style>
</head>

<body>
  <header>
    <div class="logo">Driver Handler by CROD</div>
    <nav>
      <a href="#features">Features</a>
      <a href="#install">Install</a>
      <a href="https://github.com/BLACKBIRT007/driver-manager/releases">Legacy</a>
      <a href="https://github.com/BLACKBIRT007/driver-manager">GitHub</a>
    </nav>
  </header>

  <main class="hero">
    <div>
      <div class="badge">AI-assisted Windows driver manager</div>
      <h1>Scan drivers. Review updates. Stay in control.</h1>
      <p class="lead">
        Driver Handler by CROD scans Windows devices, checks possible driver updates,
        runs from the tray, and updates itself through GitHub Releases.
      </p>

      <div class="actions">
        <a class="btn primary" href="https://github.com/BLACKBIRT007/driver-manager/releases/latest/download/Driver_Handler_By_CROD_Setup.exe">
          Download latest
        </a>
        <a class="btn secondary" href="https://github.com/BLACKBIRT007/driver-manager/releases">
          Legacy versions
        </a>
        <a class="btn secondary" href="https://github.com/BLACKBIRT007/driver-manager/actions/workflows/release.yml">
          Build new version
        </a>
      </div>

      <div class="small">
        Windows 10 / 11 · GitHub Releases · Older versions stay available
      </div>
    </div>

    <div class="mock">
      <div class="mock-head">
        <span>Driver Handler by CROD</span>
        <span>v1.0.0</span>
      </div>
      <div class="mock-body">
        <div class="mock-row">
          <div>
            <strong>NVIDIA Display Adapter</strong>
            <span class="small">Current: 546.01 · Latest: 551.23</span>
          </div>
          <div class="status">Review</div>
        </div>

        <div class="mock-row">
          <div>
            <strong>Intel Wi-Fi Controller</strong>
            <span class="small">Current: 22.140.0 · Latest: 23.10.1</span>
          </div>
          <div class="status">Review</div>
        </div>

        <div class="mock-row">
          <div>
            <strong>Realtek Audio</strong>
            <span class="small">Current driver is installed</span>
          </div>
          <div>OK</div>
        </div>
      </div>
    </div>
  </main>

  <section id="features">
    <div class="grid">
      <div class="card">
        <h3>Device scan</h3>
        <p>Uses WMI first and PowerShell as fallback to list installed Windows devices.</p>
      </div>

      <div class="card">
        <h3>Controlled updates</h3>
        <p>Shows possible updates so the user can review them before installing.</p>
      </div>

      <div class="card">
        <h3>Self-update</h3>
        <p>The launcher checks GitHub Releases and downloads the newest installer.</p>
      </div>

      <div class="card">
        <h3>One visible app</h3>
        <p>Users see DriverHandlerByCROD.exe. The core app stays internal.</p>
      </div>

      <div class="card">
        <h3>Latest + legacy</h3>
        <p>The download button always points to the latest release. Old releases remain available.</p>
      </div>

      <div class="card">
        <h3>AI-assisted</h3>
        <p>Architecture, build fixes, release pipeline, and README were co-designed with AI.</p>
      </div>
    </div>
  </section>

  <section id="install">
    <div class="card">
      <h3>Install</h3>
      <p>
        Click Download latest, run Driver_Handler_By_CROD_Setup.exe, and leave
        Start with Windows enabled if you want tray/background behaviour.
      </p>
    </div>
  </section>

  <footer>
    Built by CROD · AI-assisted · Open source on GitHub.
  </footer>
</body>
</html>
'@

Write-Host "[fix] Writing README.md"
Write-Text "README.md" @'
# Driver Handler by CROD

> **AI-assisted Windows driver manager.**  
> Scan installed devices, review possible driver updates, and keep the app itself updated through GitHub Releases.

---

## What this is

Driver Handler by CROD is a Windows desktop app made in Python.

It is designed to:

- scan installed hardware devices
- read current driver versions
- check for possible newer driver versions
- let the user update selected drivers
- run from the Windows tray
- start with Windows
- self-update from GitHub Releases
- publish installers through GitHub Actions
- provide a GitHub Pages download site

The app is not pretending to be magic. Driver updates are risky, so automatic driver installs are disabled by default.

---

## AI-built, openly

This project was heavily built, debugged, renamed, and reorganised with AI assistance.

AI helped with:

- architecture
- file layout
- PyInstaller builds
- launcher/core split
- GitHub Actions release workflow
- Inno Setup packaging
- GitHub Pages download links
- README structure
- troubleshooting failed builds and bad release paths

The final result is still human-owned code. AI helped build the structure, but every driver install should still be reviewed carefully.

---

## Final app structure

Installed folder:

```text
Driver Handler by CROD/
├─ DriverHandlerByCROD.exe
├─ DriverHandlerByCROD_Core.exe
└─ version.txt

Built by C.R.O.D. Co-developed with AI.
'@