"""
driver_installer.py - Downloads and silently installs driver packages.
Uses Windows Update / pnputil when possible, direct download otherwise.
"""

from __future__ import annotations
import os
import subprocess
import tempfile
import threading
import requests
from pathlib import Path
from typing import Callable, Optional
from device_scanner import Device
from logger import log

DOWNLOAD_TIMEOUT = 120   # seconds


class InstallResult:
    def __init__(self, device: Device, success: bool, message: str = ""):
        self.device = device
        self.success = success
        self.message = message

    def __repr__(self):
        status = "OK" if self.success else "FAILED"
        return f"<InstallResult [{status}] {self.device.display_name}: {self.message}>"


def _download_file(url: str, dest: Path, progress: Optional[Callable[[int, int], None]] = None) -> bool:
    """Downloads a file to dest. progress(downloaded_bytes, total_bytes)."""
    try:
        response = requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT)
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


def _install_inf(inf_path: Path) -> Tuple[bool, str]:
    """Installs a driver .inf file using pnputil (built into Windows)."""
    try:
        result = subprocess.run(
            ["pnputil", "/add-driver", str(inf_path), "/install"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode in (0, 3010):   # 3010 = reboot required
            return True, "Installed via pnputil" + (" (reboot required)" if result.returncode == 3010 else "")
        return False, result.stderr.strip() or result.stdout.strip()
    except Exception as e:
        return False, str(e)


def _install_exe(exe_path: Path) -> Tuple[bool, str]:
    """Runs an .exe driver installer silently."""
    silent_flags = ["/S", "/s", "/SILENT", "/quiet", "/q", "/norestart"]
    for flag in silent_flags:
        try:
            result = subprocess.run(
                [str(exe_path), flag],
                capture_output=True, timeout=300,
            )
            if result.returncode in (0, 3010, 1641):
                return True, f"Installed with flag {flag}"
        except subprocess.TimeoutExpired:
            return False, "Installer timed out"
        except Exception:
            continue
    return False, "No silent flag worked"


def install_device_driver(
    device: Device,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> InstallResult:
    """
    Downloads and installs the driver for a single device.
    progress_callback receives status strings like "Downloading…", "Installing…".
    """
    if not device.download_url:
        # Try Windows Update directly via wuauclt / usoclient
        if progress_callback:
            progress_callback("Triggering Windows Update…")
        try:
            subprocess.run(["usoclient", "StartScan"], timeout=10, capture_output=True)
        except Exception:
            pass
        return InstallResult(device, False, "No download URL available — triggered Windows Update scan instead")

    with tempfile.TemporaryDirectory(prefix="drvmgr_") as tmp:
        tmp_dir = Path(tmp)
        filename = device.download_url.split("/")[-1].split("?")[0] or "driver_package.exe"
        dest = tmp_dir / filename

        if progress_callback:
            progress_callback(f"Downloading {filename}…")

        ok = _download_file(device.download_url, dest)
        if not ok:
            return InstallResult(device, False, "Download failed")

        if progress_callback:
            progress_callback("Installing…")

        suffix = dest.suffix.lower()
        if suffix == ".inf":
            success, msg = _install_inf(dest)
        elif suffix in (".exe", ".msi"):
            success, msg = _install_exe(dest)
        elif suffix == ".zip":
            # Unzip and look for .inf
            import zipfile
            with zipfile.ZipFile(dest, "r") as zf:
                zf.extractall(tmp_dir)
            infs = list(tmp_dir.rglob("*.inf"))
            if infs:
                success, msg = _install_inf(infs[0])
            else:
                success, msg = False, "No .inf found in zip"
        else:
            success, msg = False, f"Unknown file type: {suffix}"

        log.info(f"Install {device.display_name}: {'OK' if success else 'FAILED'} — {msg}")
        return InstallResult(device, success, msg)


def install_devices_threaded(
    devices: list,
    on_result: Callable[[InstallResult], None],
    on_progress: Optional[Callable[[str, int, int], None]] = None,
):
    """
    Installs a list of devices in a background thread, one by one.
    on_result(result) called after each device.
    on_progress(status_text, current, total) called for progress updates.
    """
    def _worker():
        total = len(devices)
        for i, device in enumerate(devices):
            if on_progress:
                on_progress(f"Installing {device.display_name}…", i, total)

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
