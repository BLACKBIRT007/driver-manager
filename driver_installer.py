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